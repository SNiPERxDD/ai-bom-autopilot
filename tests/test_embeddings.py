#!/usr/bin/env python3
"""
Test script for the embedding service
"""

import os
import sys
import logging
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.embeddings.embedder import EmbeddingService
from core.schemas.models import EvidenceChunk, RefType, ScanState, Project

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chunking():
    """Test text chunking functionality"""
    print("Testing text chunking...")
    
    # Mock the database manager
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': True, 'fulltext': False}
        
        service = EmbeddingService()
        
        # Test text splitting with a very long text
        long_text = "This is a test sentence that will be repeated many times to create a very long document. " * 200  # Create a very long text
        chunks = service._split_text(long_text)
        
        print(f"Created {len(chunks)} chunks from text of {len(long_text)} characters")
        print(f"Max tokens per chunk: {service.max_tokens_per_chunk}")
        
        # Check token count to ensure we should get multiple chunks
        token_count = len(service.encoding.encode(long_text))
        print(f"Total tokens: {token_count}")
        
        if token_count > service.max_tokens_per_chunk:
            assert len(chunks) > 1, f"Should create multiple chunks for long text with {token_count} tokens"
        else:
            print("Text is short enough for single chunk")
        
        # Test chunk creation
        project_id = 1
        file_path = "test.py"
        repo_path = "/tmp/test"
        commit_sha = "abc123"
        
        # Mock file reading
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = long_text
            
            chunks = service._create_file_chunks(project_id, file_path, repo_path, commit_sha)
            
            print(f"Created {len(chunks)} EvidenceChunk objects")
            assert len(chunks) > 0, "Should create chunks"
            assert all(isinstance(chunk, EvidenceChunk) for chunk in chunks), "All should be EvidenceChunk objects"
            assert all(chunk.project_id == project_id for chunk in chunks), "All should have correct project_id"

def test_embedding_providers():
    """Test embedding provider initialization"""
    print("Testing embedding providers...")
    
    # Test OpenAI provider
    with patch.dict(os.environ, {
        'EMBED_PROVIDER': 'openai',
        'EMBEDDING_DIM': '1536',
        'OPENAI_API_KEY': 'test-key'
    }):
        with patch('core.embeddings.embedder.db_manager') as mock_db:
            mock_db.capabilities = {'vector': True, 'fulltext': False}
            
            service = EmbeddingService()
            assert service.provider == 'openai'
            assert service.dimensions == 1536
            print("✓ OpenAI provider initialized correctly")
    
    # Test Gemini provider
    with patch.dict(os.environ, {
        'EMBED_PROVIDER': 'gemini',
        'EMBEDDING_DIM': '768',
        'GEMINI_API_KEY': 'test-key'
    }):
        with patch('core.embeddings.embedder.db_manager') as mock_db:
            mock_db.capabilities = {'vector': True, 'fulltext': False}
            
            service = EmbeddingService()
            assert service.provider == 'gemini'
            assert service.dimensions == 768
            print("✓ Gemini provider initialized correctly")

def test_rrf_fusion():
    """Test Reciprocal Rank Fusion algorithm"""
    print("Testing RRF fusion...")
    
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': True, 'fulltext': False}
        
        service = EmbeddingService()
        
        # Create mock results
        vector_results = [
            ({'id': 1, 'text': 'doc1'}, 0.1),
            ({'id': 2, 'text': 'doc2'}, 0.2),
            ({'id': 3, 'text': 'doc3'}, 0.3),
        ]
        
        keyword_results = [
            ({'id': 3, 'text': 'doc3'}, 0.9),
            ({'id': 1, 'text': 'doc1'}, 0.8),
            ({'id': 4, 'text': 'doc4'}, 0.7),
        ]
        
        fused = service._reciprocal_rank_fusion(vector_results, keyword_results, limit=5)
        
        print(f"Fused {len(fused)} results")
        assert len(fused) > 0, "Should return fused results"
        assert 'rrf_score' in fused[0], "Should include RRF score"
        
        # Check that results are sorted by RRF score
        scores = [doc['rrf_score'] for doc in fused]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by RRF score descending"
        print("✓ RRF fusion working correctly")

def test_ref_type_detection():
    """Test reference type detection"""
    print("Testing reference type detection...")
    
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': True, 'fulltext': False}
        
        service = EmbeddingService()
        
        assert service._determine_ref_type("README.md") == RefType.README
        assert service._determine_ref_type("config.yaml") == RefType.CONFIG
        assert service._determine_ref_type("settings.json") == RefType.CONFIG
        assert service._determine_ref_type("main.py") == RefType.FILE
        
        print("✓ Reference type detection working correctly")

if __name__ == "__main__":
    print("Running embedding service tests...")
    
    try:
        test_chunking()
        test_embedding_providers()
        test_rrf_fusion()
        test_ref_type_detection()
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)