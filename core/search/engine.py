"""
HybridSearchEngine - Combines vector similarity and keyword search with RRF fusion

This module implements the hybrid search functionality required by task 4.4:
- ANN search using TiDB VEC_COSINE_DISTANCE queries
- FULLTEXT search using TiDB MATCH(...) AGAINST(...)
- Fallback to in-app rank-bm25 when FTS unavailable
- RRF fusion logic for combining search results

Requirements: 6.2, 6.4, 6.5
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text
from rank_bm25 import BM25Okapi
from core.db.connection import db_manager
from core.embeddings.embedder import EmbeddingService

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Represents a search result with metadata"""
    id: int
    ref_path: str
    chunk_ix: int
    text: str
    ref_type: str
    commit_sha: Optional[str]
    token_count: int
    meta: Dict[str, Any]
    score: float
    search_type: str  # 'vector', 'keyword', 'hybrid'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ref_path': self.ref_path,
            'chunk_ix': self.chunk_ix,
            'text': self.text,
            'ref_type': self.ref_type,
            'commit_sha': self.commit_sha,
            'token_count': self.token_count,
            'meta': self.meta,
            'score': self.score,
            'search_type': self.search_type
        }

class HybridSearchEngine:
    """
    Hybrid search engine combining vector similarity and keyword search
    
    Implements Requirements 6.2, 6.4, 6.5:
    - ANN search using VEC_COSINE_DISTANCE in TiDB
    - FULLTEXT search with MATCH(...) AGAINST(...)
    - Fallback to rank-bm25 when FTS unavailable
    - RRF fusion for combining results
    """
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """Initialize the hybrid search engine"""
        self.embedding_service = embedding_service or EmbeddingService()
        self.rrf_k = 60  # RRF constant for rank fusion
        
        # Log initialization status
        logger.info("🔍 HybridSearchEngine initialized")
        logger.info(f"   Vector support: {db_manager.capabilities.get('vector', False)}")
        logger.info(f"   FULLTEXT support: {db_manager.capabilities.get('fulltext', False)}")
        logger.info(f"   Embedding provider: {self.embedding_service.provider}")
    
    def search(self, project_id: int, query_text: str, top_k: int = 50) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword search
        
        Args:
            project_id: Project to search within
            query_text: Search query
            top_k: Maximum number of results to return
            
        Returns:
            List of SearchResult objects ranked by RRF score
            
        Requirements: 6.2, 6.5
        """
        try:
            logger.info(f"Performing hybrid search for project {project_id}: '{query_text[:50]}...'")
            
            # Get results from both search methods
            vector_results = self._vector_search(project_id, query_text, top_k * 2)
            keyword_results = self._keyword_search(project_id, query_text, top_k * 2)
            
            # Fuse results using RRF
            fused_results = self._reciprocal_rank_fusion(vector_results, keyword_results, top_k)
            
            logger.info(f"Hybrid search completed: {len(vector_results)} vector + {len(keyword_results)} keyword → {len(fused_results)} fused")
            
            return fused_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            # Fallback to basic search
            return self._fallback_search(project_id, query_text, top_k)
    
    def _vector_search(self, project_id: int, query_text: str, limit: int) -> List[SearchResult]:
        """
        Perform ANN search using TiDB VEC_COSINE_DISTANCE
        
        Requirements: 6.2 - ANN search using VEC_COSINE_DISTANCE in TiDB
        """
        if not db_manager.capabilities.get('vector', False):
            logger.debug("Vector search unavailable - no vector support")
            return []
        
        if not self.embedding_service._has_embedding_client():
            logger.debug("Vector search unavailable - no embedding client")
            return []
        
        try:
            # Generate query embedding
            query_vector = self.embedding_service.get_embedding(query_text)
            
            with db_manager.get_session() as session:
                # Execute VEC_COSINE_DISTANCE query
                result = session.execute(text("""
                    SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta,
                           VEC_COSINE_DISTANCE(emb, :query_vector) AS distance
                    FROM evidence_chunks
                    WHERE project_id = :project_id
                    AND emb IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT :limit
                """), {
                    'project_id': project_id,
                    'query_vector': json.dumps(query_vector),
                    'limit': limit
                })
                
                results = []
                for row in result:
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 - row.distance if row.distance is not None else 0.0
                    
                    search_result = SearchResult(
                        id=row.id,
                        ref_path=row.ref_path,
                        chunk_ix=row.chunk_ix,
                        text=row.text,
                        ref_type=row.ref_type,
                        commit_sha=row.commit_sha,
                        token_count=row.token_count,
                        meta=json.loads(row.meta) if row.meta else {},
                        score=similarity_score,
                        search_type='vector'
                    )
                    results.append(search_result)
                
                logger.debug(f"Vector search returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _keyword_search(self, project_id: int, query_text: str, limit: int) -> List[SearchResult]:
        """
        Perform keyword search using FULLTEXT or BM25 fallback
        
        Requirements: 6.4 - FULLTEXT search with fallback to BM25
        """
        # Try FULLTEXT search first if available
        if db_manager.capabilities.get('fulltext', False):
            try:
                return self._fulltext_search(project_id, query_text, limit)
            except Exception as e:
                logger.warning(f"FULLTEXT search failed, falling back to BM25: {e}")
                # Disable FULLTEXT for future searches and log the fallback
                db_manager.capabilities['fulltext'] = False
                logger.info("FTS disabled -> BM25(app)")
        
        # Fallback to BM25
        return self._bm25_search(project_id, query_text, limit)
    
    def _fulltext_search(self, project_id: int, query_text: str, limit: int) -> List[SearchResult]:
        """
        Perform FULLTEXT search using TiDB MATCH(...) AGAINST(...)
        
        Requirements: 6.4 - TiDB MATCH(...) AGAINST(...) for FULLTEXT search
        """
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta,
                       MATCH(text) AGAINST (:query IN NATURAL LANGUAGE MODE) AS relevance_score
                FROM evidence_chunks
                WHERE project_id = :project_id
                AND MATCH(text) AGAINST (:query IN NATURAL LANGUAGE MODE)
                ORDER BY relevance_score DESC
                LIMIT :limit
            """), {
                'project_id': project_id,
                'query': query_text,
                'limit': limit
            })
            
            results = []
            for row in result:
                search_result = SearchResult(
                    id=row.id,
                    ref_path=row.ref_path,
                    chunk_ix=row.chunk_ix,
                    text=row.text,
                    ref_type=row.ref_type,
                    commit_sha=row.commit_sha,
                    token_count=row.token_count,
                    meta=json.loads(row.meta) if row.meta else {},
                    score=float(row.relevance_score) if row.relevance_score else 0.0,
                    search_type='fulltext'
                )
                results.append(search_result)
            
            logger.debug(f"FULLTEXT search returned {len(results)} results")
            return results
    
    def _bm25_search(self, project_id: int, query_text: str, limit: int) -> List[SearchResult]:
        """
        Perform BM25 search using rank-bm25 library as fallback
        
        Requirements: 6.4 - Fallback to in-app rank-bm25 when FTS unavailable
        """
        try:
            with db_manager.get_session() as session:
                # Get all chunks for the project
                result = session.execute(text("""
                    SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta
                    FROM evidence_chunks
                    WHERE project_id = :project_id
                    ORDER BY id
                """), {'project_id': project_id})
                
                chunks = []
                chunk_data = []
                
                for row in result:
                    chunks.append(row.text.lower().split())  # Tokenize for BM25
                    chunk_data.append({
                        'id': row.id,
                        'ref_path': row.ref_path,
                        'chunk_ix': row.chunk_ix,
                        'text': row.text,
                        'ref_type': row.ref_type,
                        'commit_sha': row.commit_sha,
                        'token_count': row.token_count,
                        'meta': json.loads(row.meta) if row.meta else {}
                    })
                
                if not chunks:
                    logger.debug("No chunks found for BM25 search")
                    return []
                
                # Initialize BM25 and get scores
                bm25 = BM25Okapi(chunks)
                query_tokens = query_text.lower().split()
                scores = bm25.get_scores(query_tokens)
                
                # Create results with scores
                results = []
                for i, score in enumerate(scores):
                    if score > 0:  # Only include relevant results
                        search_result = SearchResult(
                            id=chunk_data[i]['id'],
                            ref_path=chunk_data[i]['ref_path'],
                            chunk_ix=chunk_data[i]['chunk_ix'],
                            text=chunk_data[i]['text'],
                            ref_type=chunk_data[i]['ref_type'],
                            commit_sha=chunk_data[i]['commit_sha'],
                            token_count=chunk_data[i]['token_count'],
                            meta=chunk_data[i]['meta'],
                            score=float(score),
                            search_type='bm25'
                        )
                        results.append(search_result)
                
                # Sort by score and limit
                results.sort(key=lambda x: x.score, reverse=True)
                results = results[:limit]
                
                logger.debug(f"BM25 search returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, vector_results: List[SearchResult], 
                               keyword_results: List[SearchResult], 
                               limit: int) -> List[SearchResult]:
        """
        Fuse vector and keyword search results using Reciprocal Rank Fusion
        
        Requirements: 6.5 - RRF fusion logic for combining search results
        """
        # Create rank maps for both result sets
        vector_ranks = {result.id: rank + 1 for rank, result in enumerate(vector_results)}
        keyword_ranks = {result.id: rank + 1 for rank, result in enumerate(keyword_results)}
        
        # Create lookup maps for result data
        vector_lookup = {result.id: result for result in vector_results}
        keyword_lookup = {result.id: result for result in keyword_results}
        
        # Get all unique document IDs
        all_doc_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())
        
        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_doc_ids:
            vector_rank = vector_ranks.get(doc_id, float('inf'))
            keyword_rank = keyword_ranks.get(doc_id, float('inf'))
            
            # RRF formula: 1/(k + rank)
            vector_score = 1 / (self.rrf_k + vector_rank) if vector_rank != float('inf') else 0
            keyword_score = 1 / (self.rrf_k + keyword_rank) if keyword_rank != float('inf') else 0
            
            rrf_scores[doc_id] = vector_score + keyword_score
        
        # Sort by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Build final results
        fused_results = []
        for doc_id in sorted_doc_ids[:limit]:
            # Prefer vector result if available, otherwise use keyword result
            if doc_id in vector_lookup:
                result = vector_lookup[doc_id]
                search_type = 'hybrid' if doc_id in keyword_lookup else 'vector'
            else:
                result = keyword_lookup[doc_id]
                search_type = 'keyword'
            
            # Create new result with RRF score
            fused_result = SearchResult(
                id=result.id,
                ref_path=result.ref_path,
                chunk_ix=result.chunk_ix,
                text=result.text,
                ref_type=result.ref_type,
                commit_sha=result.commit_sha,
                token_count=result.token_count,
                meta=result.meta,
                score=rrf_scores[doc_id],
                search_type=search_type
            )
            fused_results.append(fused_result)
        
        logger.debug(f"RRF fusion: {len(vector_results)} vector + {len(keyword_results)} keyword → {len(fused_results)} fused")
        return fused_results
    
    def _fallback_search(self, project_id: int, query_text: str, limit: int) -> List[SearchResult]:
        """
        Basic fallback search using LIKE when all other methods fail
        """
        logger.warning("Using basic LIKE search as fallback")
        
        try:
            with db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta
                    FROM evidence_chunks
                    WHERE project_id = :project_id
                    AND text LIKE :query
                    ORDER BY id DESC
                    LIMIT :limit
                """), {
                    'project_id': project_id,
                    'query': f'%{query_text}%',
                    'limit': limit
                })
                
                results = []
                for row in result:
                    search_result = SearchResult(
                        id=row.id,
                        ref_path=row.ref_path,
                        chunk_ix=row.chunk_ix,
                        text=row.text,
                        ref_type=row.ref_type,
                        commit_sha=row.commit_sha,
                        token_count=row.token_count,
                        meta=json.loads(row.meta) if row.meta else {},
                        score=1.0,  # Basic score for fallback
                        search_type='fallback'
                    )
                    results.append(search_result)
                
                logger.debug(f"Fallback search returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    def get_search_capabilities(self) -> Dict[str, Any]:
        """
        Get current search capabilities and status
        
        Returns information about available search methods and their status
        """
        return {
            'vector_search': {
                'available': db_manager.capabilities.get('vector', False),
                'embedding_provider': self.embedding_service.provider,
                'embedding_client': self.embedding_service._has_embedding_client(),
                'dimensions': self.embedding_service.dimensions
            },
            'fulltext_search': {
                'available': db_manager.capabilities.get('fulltext', False),
                'fallback_to_bm25': True
            },
            'hybrid_fusion': {
                'method': 'reciprocal_rank_fusion',
                'rrf_k': self.rrf_k
            },
            'fallback_search': {
                'method': 'like_search',
                'available': True
            }
        }

# Global search engine instance
search_engine = HybridSearchEngine()