import openai
import hashlib
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from core.schemas.models import EvidenceChunk, RefType, ScanState
from core.db.connection import db_manager
from sqlalchemy import text
from decouple import config
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Handles text embeddings and chunking with multi-provider support"""
    
    def __init__(self):
        self.provider = config('EMBED_PROVIDER', default='openai').lower()
        self.encoding = None  # Will be initialized by provider
        self.max_tokens_per_chunk = 800
        self.chunk_overlap = 100
        
        # Initialize provider-specific clients
        self.openai_client = None
        self.gemini_client = None
        self.model = None
        self.dimensions = None
        
        # Validate and initialize provider
        self._initialize_provider()
        
        # Validate dimensions configuration
        self._validate_dimensions()
        
        # Log startup configuration (Requirement 7.4)
        logger.info(f"🚀 Embedding Service Initialized")
        logger.info(f"   Provider: {self.provider}")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Dimensions: {self.dimensions}")
        logger.info(f"   Client Available: {self._has_embedding_client()}")
    
    def _initialize_provider(self):
        """Initialize the embedding provider based on configuration"""
        if self.provider == 'openai':
            self._initialize_openai()
        elif self.provider == 'gemini':
            self._initialize_gemini()
        else:
            logger.error(f"❌ Unsupported embedding provider: {self.provider}")
            logger.error("   Supported providers: openai, gemini")
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    def _initialize_openai(self):
        """Initialize OpenAI embedding provider (Requirement 7.1)"""
        try:
            # Import tiktoken only when using OpenAI
            import tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")
            
            api_key = config('OPENAI_API_KEY', default=None)
            if not api_key or api_key == 'sk-test':
                logger.warning("⚠️  OpenAI API key not configured or using test key")
                self.openai_client = None
            else:
                # Initialize OpenAI client with minimal parameters to avoid version issues
                try:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    logger.info("✅ OpenAI client initialized successfully")
                except TypeError as te:
                    # Handle older OpenAI client versions
                    logger.warning(f"⚠️  OpenAI client initialization issue: {te}")
                    logger.warning("   Trying alternative initialization...")
                    openai.api_key = api_key
                    self.openai_client = openai
                    logger.info("✅ OpenAI client initialized with legacy method")
            
            self.model = config('EMBEDDING_MODEL', default='text-embedding-3-small')
            
            # OpenAI expects 1536 dimensions by default (Requirement 7.1)
            expected_dim = 1536
            configured_dim = config('EMBEDDING_DIM', cast=int, default=None)
            
            if configured_dim is None:
                logger.warning(f"⚠️  EMBEDDING_DIM not set, using OpenAI default: {expected_dim}")
                self.dimensions = expected_dim
            else:
                self.dimensions = configured_dim
                if configured_dim != expected_dim:
                    logger.warning(f"⚠️  EMBEDDING_DIM ({configured_dim}) differs from OpenAI default ({expected_dim})")
                    logger.warning("   Ensure this matches your model's output dimensions")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI provider: {e}")
            self.openai_client = None
            self.model = "openai-failed"
            self.dimensions = 1536  # Fallback
    
    def _initialize_gemini(self):
        """Initialize Gemini embedding provider (Requirement 7.2)"""
        try:
            # For Gemini, we use a simple token counter (approximate)
            self.encoding = None  # Will use _count_tokens_simple method
            
            api_key = config('GEMINI_API_KEY', default=None)
            if not api_key:
                logger.warning("⚠️  Gemini API key not configured")
                self.gemini_client = None
            else:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.gemini_client = genai
                logger.info("✅ Gemini client initialized successfully")
            
            self.model = config('EMBEDDING_MODEL', default='models/embedding-001')
            
            # Gemini expects 768 dimensions by default (Requirement 7.2)
            expected_dim = 768
            configured_dim = config('EMBEDDING_DIM', cast=int, default=None)
            
            if configured_dim is None:
                logger.warning(f"⚠️  EMBEDDING_DIM not set, using Gemini default: {expected_dim}")
                self.dimensions = expected_dim
            else:
                self.dimensions = configured_dim
                if configured_dim != expected_dim:
                    logger.warning(f"⚠️  EMBEDDING_DIM ({configured_dim}) differs from Gemini default ({expected_dim})")
                    logger.warning("   Ensure this matches your model's output dimensions")
            
        except ImportError:
            logger.error("❌ google-generativeai package not installed")
            logger.error("   Install with: pip install google-generativeai")
            self.gemini_client = None
            self.model = "gemini-missing-package"
            self.dimensions = 768  # Fallback
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini provider: {e}")
            self.gemini_client = None
            self.model = "gemini-failed"
            self.dimensions = 768  # Fallback
    
    def _validate_dimensions(self):
        """Validate embedding dimensions configuration (Requirement 7.5)"""
        if self.dimensions is None:
            error_msg = "EMBEDDING_DIM environment variable is required to prevent data mismatch"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        if not isinstance(self.dimensions, int) or self.dimensions <= 0:
            error_msg = f"EMBEDDING_DIM must be a positive integer, got: {self.dimensions}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # Validate dimensions match expected values for each provider
        if self.provider == 'openai' and self.dimensions not in [1536, 3072]:
            logger.warning(f"⚠️  Unusual dimension count for OpenAI: {self.dimensions}")
            logger.warning("   Common OpenAI dimensions: 1536 (text-embedding-3-small), 3072 (text-embedding-3-large)")
        elif self.provider == 'gemini' and self.dimensions != 768:
            logger.warning(f"⚠️  Unusual dimension count for Gemini: {self.dimensions}")
            logger.warning("   Standard Gemini dimension: 768 (models/embedding-001)")
        
        logger.info(f"✅ Embedding dimensions validated: {self.dimensions}")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text, provider-agnostic"""
        if self.encoding:
            # Use tiktoken for OpenAI
            return len(self.encoding.encode(text))
        else:
            # Simple approximation for Gemini (roughly 4 chars per token)
            return len(text) // 4
    
    def _encode_text(self, text: str) -> List[int]:
        """Encode text to tokens, provider-agnostic"""
        if self.encoding:
            return self.encoding.encode(text)
        else:
            # For Gemini, create fake tokens (split by words)
            words = text.split()
            return list(range(len(words)))
    
    def _decode_tokens(self, tokens: List[int], original_text: str = None) -> str:
        """Decode tokens to text, provider-agnostic"""
        if self.encoding:
            return self.encoding.decode(tokens)
        else:
            # For Gemini, use word-based approximation
            if original_text:
                words = original_text.split()
                return ' '.join(words[:len(tokens)])
            return ""
    
    def process_evidence(self, state: ScanState) -> ScanState:
        """Process and embed evidence chunks"""
        try:
            repo_path = f"/tmp/repos/{state.project.repo_url.split('/')[-1].replace('.git', '')}"
            
            # Process files
            for file_path in state.files:
                chunks = self._create_file_chunks(state.project.id, file_path, repo_path, state.commit_sha)
                state.evidence_chunks.extend(chunks)
            
            # Process HF cards (if any were fetched)
            # This would be populated by the HF fetcher
            
            # Batch embed chunks
            self._batch_embed_chunks(state.evidence_chunks)
            
            # Store in database
            self._store_chunks(state.evidence_chunks)
            
            logger.info(f"Processed {len(state.evidence_chunks)} evidence chunks")
            
        except Exception as e:
            logger.error(f"Failed to process evidence: {e}")
            state.error = str(e)
        
        return state
    
    def _create_file_chunks(self, project_id: int, file_path: str, repo_path: str, commit_sha: str) -> List[EvidenceChunk]:
        """Create chunks from a file"""
        chunks = []
        
        try:
            full_path = f"{repo_path}/{file_path}"
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Determine reference type
            ref_type = self._determine_ref_type(file_path)
            
            # Split into chunks
            text_chunks = self._split_text(content)
            
            for i, chunk_text in enumerate(text_chunks):
                token_count = self._count_tokens(chunk_text)
                
                chunk = EvidenceChunk(
                    project_id=project_id,
                    ref_type=ref_type,
                    ref_path=file_path,
                    commit_sha=commit_sha,
                    chunk_ix=i,
                    text=chunk_text,
                    token_count=token_count,
                    meta={
                        'file_size': len(content),
                        'total_chunks': len(text_chunks)
                    }
                )
                chunks.append(chunk)
        
        except Exception as e:
            logger.warning(f"Failed to create chunks for {file_path}: {e}")
        
        return chunks
    
    def _determine_ref_type(self, file_path: str) -> RefType:
        """Determine the reference type of a file"""
        file_path_lower = file_path.lower()
        
        if 'readme' in file_path_lower:
            return RefType.README
        elif file_path_lower.endswith(('.yaml', '.yml', '.json')):
            return RefType.CONFIG
        else:
            return RefType.FILE
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        tokens = self._encode_text(text)
        chunks = []
        
        if len(tokens) <= self.max_tokens_per_chunk:
            # Text is short enough to fit in one chunk
            return [text]
        
        start = 0
        while start < len(tokens):
            end = min(start + self.max_tokens_per_chunk, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self._decode_tokens(chunk_tokens, text)
            
            # For non-tiktoken providers, use character-based chunking as fallback
            if not self.encoding and chunk_text == "":
                # Fall back to character-based chunking
                char_start = (start * len(text)) // len(tokens)
                char_end = (end * len(text)) // len(tokens)
                chunk_text = text[char_start:char_end]
            
            chunks.append(chunk_text)
            
            if end >= len(tokens):
                break
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= end:  # Prevent infinite loop
                start = end
        
        return chunks
    
    def _batch_embed_chunks(self, chunks: List[EvidenceChunk], batch_size: int = 100):
        """Embed chunks in batches using the configured provider"""
        if not db_manager.capabilities['vector']:
            logger.info("Vector support not available, skipping embeddings")
            return
        
        if not self._has_embedding_client():
            logger.warning("No embedding client available, skipping embeddings")
            return
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [chunk.text for chunk in batch]
            
            try:
                embeddings = self._get_embeddings(texts)
                
                for j, embedding in enumerate(embeddings):
                    batch[j].emb = embedding
                
                logger.info(f"Embedded batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size} using {self.provider}")
                
            except Exception as e:
                logger.error(f"Failed to embed batch {i//batch_size + 1}: {e}")
    
    def _has_embedding_client(self) -> bool:
        """Check if embedding client is available"""
        if self.provider == 'openai':
            # Check if we have a client and a valid API key
            api_key = config('OPENAI_API_KEY', default=None)
            return self.openai_client is not None and api_key and api_key != 'sk-test'
        elif self.provider == 'gemini':
            # Check if we have a client and a valid API key
            api_key = config('GEMINI_API_KEY', default=None)
            return self.gemini_client is not None and api_key is not None
        return False
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get current provider configuration info"""
        return {
            'provider': self.provider,
            'model': self.model,
            'dimensions': self.dimensions,
            'client_available': self._has_embedding_client(),
            'status': 'ready' if self._has_embedding_client() else 'not_configured'
        }
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from the configured provider"""
        if not self._has_embedding_client():
            raise ValueError(f"No client available for provider: {self.provider}")
        
        if self.provider == 'openai':
            return self._get_openai_embeddings(texts)
        elif self.provider == 'gemini':
            return self._get_gemini_embeddings(texts)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _get_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI API"""
        try:
            # Handle both new and legacy OpenAI client APIs
            if hasattr(self.openai_client, 'embeddings'):
                # New OpenAI client (v1.0+)
                params = {
                    'model': self.model,
                    'input': texts
                }
                
                # Only add dimensions parameter if it's supported by the model
                if self.model in ['text-embedding-3-small', 'text-embedding-3-large']:
                    params['dimensions'] = self.dimensions
                
                response = self.openai_client.embeddings.create(**params)
                embeddings = [data.embedding for data in response.data]
            else:
                # Legacy OpenAI client (pre-v1.0)
                response = openai.Embedding.create(
                    model=self.model,
                    input=texts
                )
                embeddings = [data['embedding'] for data in response['data']]
            
            # Validate embedding dimensions
            if embeddings and len(embeddings[0]) != self.dimensions:
                logger.warning(f"⚠️  Expected {self.dimensions} dimensions, got {len(embeddings[0])}")
                logger.warning("   Consider updating EMBEDDING_DIM to match actual output")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ OpenAI embedding request failed: {e}")
            raise
    
    def _get_gemini_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Gemini API"""
        try:
            embeddings = []
            for text in texts:
                result = self.gemini_client.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = result['embedding']
                
                # Validate embedding dimensions
                if len(embedding) != self.dimensions:
                    logger.warning(f"⚠️  Expected {self.dimensions} dimensions, got {len(embedding)}")
                    logger.warning("   Consider updating EMBEDDING_DIM to match actual output")
                
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Gemini embedding request failed: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Get a single embedding for a text"""
        if not self._has_embedding_client():
            raise ValueError(f"No embedding client available for provider: {self.provider}")
        return self._get_embeddings([text])[0]
    
    def validate_provider_config(self) -> Dict[str, Any]:
        """Validate the current provider configuration"""
        validation_result = {
            'provider': self.provider,
            'model': self.model,
            'dimensions': self.dimensions,
            'client_available': self._has_embedding_client(),
            'config_valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check if client is available
        if not self._has_embedding_client():
            validation_result['config_valid'] = False
            if self.provider == 'openai':
                validation_result['errors'].append("OpenAI API key not configured or invalid")
            elif self.provider == 'gemini':
                validation_result['errors'].append("Gemini API key not configured or invalid")
        
        # Check dimensions configuration
        if self.provider == 'openai':
            if self.dimensions not in [1536, 3072]:
                validation_result['warnings'].append(f"Unusual OpenAI dimensions: {self.dimensions}")
        elif self.provider == 'gemini':
            if self.dimensions != 768:
                validation_result['warnings'].append(f"Unusual Gemini dimensions: {self.dimensions}")
        
        # Skip embedding test for now - just validate configuration
        validation_result['warnings'].append("Embedding test skipped - requires valid API key for live testing")
        
        return validation_result
    
    def _store_chunks(self, chunks: List[EvidenceChunk]):
        """Store chunks in database with hash-based deduplication"""
        with db_manager.get_session() as session:
            for chunk in chunks:
                try:
                    # Create hash for deduplication
                    chunk_hash = hashlib.sha256(
                        f"{chunk.project_id}:{chunk.ref_path}:{chunk.chunk_ix}:{chunk.text}".encode()
                    ).hexdigest()
                    
                    # Check if chunk already exists
                    existing = session.execute(text("""
                        SELECT id FROM evidence_chunks 
                        WHERE project_id = :project_id 
                        AND ref_path = :ref_path 
                        AND chunk_ix = :chunk_ix
                        AND SHA2(CONCAT(project_id, ':', ref_path, ':', chunk_ix, ':', text), 256) = :chunk_hash
                    """), {
                        'project_id': chunk.project_id,
                        'ref_path': chunk.ref_path,
                        'chunk_ix': chunk.chunk_ix,
                        'chunk_hash': chunk_hash
                    }).fetchone()
                    
                    if existing:
                        continue  # Skip duplicate
                    
                    # Insert new chunk
                    if db_manager.capabilities['vector'] and chunk.emb:
                        # Convert embedding to proper TiDB vector format
                        emb_str = json.dumps(chunk.emb)
                        session.execute(text("""
                            INSERT INTO evidence_chunks 
                            (project_id, ref_type, ref_path, commit_sha, chunk_ix, text, token_count, emb, meta)
                            VALUES (:project_id, :ref_type, :ref_path, :commit_sha, :chunk_ix, :text, :token_count, :emb, :meta)
                        """), {
                            'project_id': chunk.project_id,
                            'ref_type': chunk.ref_type.value,
                            'ref_path': chunk.ref_path,
                            'commit_sha': chunk.commit_sha,
                            'chunk_ix': chunk.chunk_ix,
                            'text': chunk.text,
                            'token_count': chunk.token_count,
                            'emb': emb_str,
                            'meta': json.dumps(chunk.meta)
                        })
                    else:
                        session.execute(text("""
                            INSERT INTO evidence_chunks 
                            (project_id, ref_type, ref_path, commit_sha, chunk_ix, text, token_count, meta)
                            VALUES (:project_id, :ref_type, :ref_path, :commit_sha, :chunk_ix, :text, :token_count, :meta)
                        """), {
                            'project_id': chunk.project_id,
                            'ref_type': chunk.ref_type.value,
                            'ref_path': chunk.ref_path,
                            'commit_sha': chunk.commit_sha,
                            'chunk_ix': chunk.chunk_ix,
                            'text': chunk.text,
                            'token_count': chunk.token_count,
                            'meta': json.dumps(chunk.meta)
                        })
                
                except Exception as e:
                    logger.warning(f"Failed to store chunk: {e}")
            
            session.commit()
    
    def search_similar(self, project_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Hybrid search using both vector similarity and keyword search with RRF fusion"""
        try:
            # Get both vector and keyword results
            vector_results = self._vector_search(project_id, query, limit * 2)  # Get more for fusion
            keyword_results = self._keyword_search(project_id, query, limit * 2)
            
            # Fuse results using Reciprocal Rank Fusion (RRF)
            fused_results = self._reciprocal_rank_fusion(vector_results, keyword_results, limit)
            
            logger.info(f"Hybrid search returned {len(fused_results)} results for query: {query[:50]}...")
            return fused_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return self._fallback_search(project_id, query, limit)
    
    def _vector_search(self, project_id: int, query: str, limit: int) -> List[Tuple[Dict[str, Any], float]]:
        """Perform vector similarity search"""
        if not db_manager.capabilities['vector'] or not self._has_embedding_client():
            return []
        
        try:
            # Get query embedding
            query_emb = self._get_embeddings([query])[0]
            
            with db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta,
                           VEC_COSINE_DISTANCE(emb, :query_emb) AS distance
                    FROM evidence_chunks
                    WHERE project_id = :project_id
                    ORDER BY distance ASC
                    LIMIT :limit
                """), {
                    'project_id': project_id,
                    'query_emb': json.dumps(query_emb),
                    'limit': limit
                })
                
                return [(dict(row._mapping), row.distance) for row in result]
        
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _keyword_search(self, project_id: int, query: str, limit: int) -> List[Tuple[Dict[str, Any], float]]:
        """Perform keyword search using FULLTEXT or BM25 fallback"""
        with db_manager.get_session() as session:
            if db_manager.capabilities['fulltext']:
                # Use FULLTEXT search
                try:
                    result = session.execute(text("""
                        SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta,
                               MATCH(text) AGAINST (:query IN NATURAL LANGUAGE MODE) AS score
                        FROM evidence_chunks
                        WHERE project_id = :project_id
                        AND MATCH(text) AGAINST (:query IN NATURAL LANGUAGE MODE)
                        ORDER BY score DESC
                        LIMIT :limit
                    """), {
                        'project_id': project_id,
                        'query': query,
                        'limit': limit
                    })
                    
                    return [(dict(row._mapping), row.score) for row in result]
                    
                except Exception as e:
                    logger.warning(f"FULLTEXT search failed, falling back to BM25: {e}")
                    db_manager.capabilities['fulltext'] = False
                    logger.info("FTS disabled -> BM25(app)")
            
            # Fallback to BM25
            return self._bm25_search(project_id, query, limit)
    
    def _bm25_search(self, project_id: int, query: str, limit: int) -> List[Tuple[Dict[str, Any], float]]:
        """Perform BM25 search using rank-bm25 library"""
        try:
            with db_manager.get_session() as session:
                # Get all chunks for the project
                result = session.execute(text("""
                    SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta
                    FROM evidence_chunks
                    WHERE project_id = :project_id
                """), {'project_id': project_id})
                
                chunks = [dict(row._mapping) for row in result]
                
                if not chunks:
                    return []
                
                # Tokenize documents for BM25
                tokenized_docs = [chunk['text'].lower().split() for chunk in chunks]
                bm25 = BM25Okapi(tokenized_docs)
                
                # Get BM25 scores
                query_tokens = query.lower().split()
                scores = bm25.get_scores(query_tokens)
                
                # Combine chunks with scores and sort
                scored_chunks = [(chunks[i], scores[i]) for i in range(len(chunks))]
                scored_chunks.sort(key=lambda x: x[1], reverse=True)
                
                return scored_chunks[:limit]
                
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, vector_results: List[Tuple[Dict[str, Any], float]], 
                               keyword_results: List[Tuple[Dict[str, Any], float]], 
                               limit: int, k: int = 60) -> List[Dict[str, Any]]:
        """Fuse vector and keyword search results using Reciprocal Rank Fusion"""
        # Create rank maps
        vector_ranks = {result[0]['id']: rank + 1 for rank, result in enumerate(vector_results)}
        keyword_ranks = {result[0]['id']: rank + 1 for rank, result in enumerate(keyword_results)}
        
        # Collect all unique document IDs
        all_doc_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())
        
        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_doc_ids:
            vector_rank = vector_ranks.get(doc_id, float('inf'))
            keyword_rank = keyword_ranks.get(doc_id, float('inf'))
            
            # RRF formula: 1/(k + rank)
            vector_score = 1 / (k + vector_rank) if vector_rank != float('inf') else 0
            keyword_score = 1 / (k + keyword_rank) if keyword_rank != float('inf') else 0
            
            rrf_scores[doc_id] = vector_score + keyword_score
        
        # Sort by RRF score and get documents
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Get document data (prefer vector results, fallback to keyword results)
        result_docs = []
        for doc_id in sorted_doc_ids[:limit]:
            doc_data = None
            
            # Find document in vector results first
            for result, _ in vector_results:
                if result['id'] == doc_id:
                    doc_data = result.copy()
                    doc_data['rrf_score'] = rrf_scores[doc_id]
                    doc_data['search_type'] = 'vector+keyword'
                    break
            
            # Fallback to keyword results
            if doc_data is None:
                for result, _ in keyword_results:
                    if result['id'] == doc_id:
                        doc_data = result.copy()
                        doc_data['rrf_score'] = rrf_scores[doc_id]
                        doc_data['search_type'] = 'keyword'
                        break
            
            if doc_data:
                result_docs.append(doc_data)
        
        return result_docs
    
    def _fallback_search(self, project_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback search using LIKE when all else fails"""
        logger.warning("Using basic LIKE search as fallback")
        
        with db_manager.get_session() as session:
            # Use simple LIKE search as last resort
            result = session.execute(text("""
                SELECT id, ref_path, chunk_ix, text, ref_type, commit_sha, token_count, meta, 1 AS score
                FROM evidence_chunks
                WHERE project_id = :project_id
                AND text LIKE :query
                ORDER BY id DESC
                LIMIT :limit
            """), {
                'project_id': project_id,
                'query': f'%{query}%',
                'limit': limit
            })
            
            return [dict(row._mapping) for row in result]