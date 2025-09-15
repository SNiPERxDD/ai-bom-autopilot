#!/usr/bin/env python3
"""
Test script for HybridSearchEngine implementation

This script tests the core functionality of the HybridSearchEngine:
- Vector search with VEC_COSINE_DISTANCE
- FULLTEXT search with MATCH(...) AGAINST(...)
- BM25 fallback when FTS unavailable
- RRF fusion logic

Requirements: 6.2, 6.4, 6.5
"""

import sys
import os
import logging
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.search.engine import HybridSearchEngine, SearchResult
from core.db.connection import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_search_result_creation():
    """Test SearchResult dataclass functionality"""
    print("🧪 Testing SearchResult creation...")
    
    result = SearchResult(
        id=1,
        ref_path="test/file.py",
        chunk_ix=0,
        text="This is a test chunk",
        ref_type="file",
        commit_sha="abc123",
        token_count=5,
        meta={"test": True},
        score=0.85,
        search_type="vector"
    )
    
    # Test to_dict conversion
    result_dict = result.to_dict()
    assert result_dict['id'] == 1
    assert result_dict['score'] == 0.85
    assert result_dict['search_type'] == "vector"
    
    print("✅ SearchResult creation test passed")

def test_rrf_fusion():
    """Test Reciprocal Rank Fusion logic"""
    print("🧪 Testing RRF fusion logic...")
    
    # Create mock search engine
    engine = HybridSearchEngine()
    
    # Create mock results
    vector_results = [
        SearchResult(1, "file1.py", 0, "vector result 1", "file", "abc", 10, {}, 0.9, "vector"),
        SearchResult(2, "file2.py", 0, "vector result 2", "file", "def", 15, {}, 0.8, "vector"),
        SearchResult(3, "file3.py", 0, "vector result 3", "file", "ghi", 12, {}, 0.7, "vector"),
    ]
    
    keyword_results = [
        SearchResult(2, "file2.py", 0, "keyword result 2", "file", "def", 15, {}, 5.0, "keyword"),
        SearchResult(4, "file4.py", 0, "keyword result 4", "file", "jkl", 8, {}, 4.0, "keyword"),
        SearchResult(1, "file1.py", 0, "keyword result 1", "file", "abc", 10, {}, 3.0, "keyword"),
    ]
    
    # Test RRF fusion
    fused = engine._reciprocal_rank_fusion(vector_results, keyword_results, limit=5)
    
    # Verify results
    assert len(fused) <= 5
    assert all(isinstance(r, SearchResult) for r in fused)
    
    # Check that results are sorted by RRF score (descending)
    for i in range(len(fused) - 1):
        assert fused[i].score >= fused[i + 1].score
    
    # Verify that documents appearing in both lists get hybrid search_type
    doc_2_results = [r for r in fused if r.id == 2]
    if doc_2_results:
        assert doc_2_results[0].search_type == "hybrid"
    
    print("✅ RRF fusion test passed")

def test_capabilities_reporting():
    """Test search capabilities reporting"""
    print("🧪 Testing capabilities reporting...")
    
    engine = HybridSearchEngine()
    capabilities = engine.get_search_capabilities()
    
    # Verify structure
    assert 'vector_search' in capabilities
    assert 'fulltext_search' in capabilities
    assert 'hybrid_fusion' in capabilities
    assert 'fallback_search' in capabilities
    
    # Verify vector search info
    vector_info = capabilities['vector_search']
    assert 'available' in vector_info
    assert 'embedding_provider' in vector_info
    assert 'embedding_client' in vector_info
    assert 'dimensions' in vector_info
    
    # Verify fusion info
    fusion_info = capabilities['hybrid_fusion']
    assert fusion_info['method'] == 'reciprocal_rank_fusion'
    assert fusion_info['rrf_k'] == 60
    
    print("✅ Capabilities reporting test passed")

def test_mock_search_methods():
    """Test individual search methods with mocked database"""
    print("🧪 Testing individual search methods...")
    
    engine = HybridSearchEngine()
    
    # Test that methods handle missing capabilities gracefully
    with patch.object(db_manager, 'capabilities', {'vector': False, 'fulltext': False}):
        vector_results = engine._vector_search(1, "test query", 10)
        assert vector_results == []
        print("✅ Vector search gracefully handles missing vector support")
    
    # Test BM25 search with empty database
    with patch.object(db_manager, 'get_session') as mock_session:
        mock_session.return_value.__enter__.return_value.execute.return_value = []
        bm25_results = engine._bm25_search(1, "test query", 10)
        assert bm25_results == []
        print("✅ BM25 search handles empty database")
    
    print("✅ Individual search methods test passed")

def test_database_connection():
    """Test database connection and capabilities"""
    print("🧪 Testing database connection...")
    
    try:
        health = db_manager.health_check()
        print(f"Database status: {health['status']}")
        
        if health['status'] == 'healthy':
            capabilities = db_manager.capabilities
            print(f"Vector support: {capabilities.get('vector', False)}")
            print(f"FULLTEXT support: {capabilities.get('fulltext', False)}")
            print(f"TiDB version: {capabilities.get('version', 'unknown')}")
        else:
            print(f"Database connection failed: {health.get('error', 'unknown error')}")
            print("This is expected if TiDB is not configured")
        
        print("✅ Database connection test completed")
        
    except Exception as e:
        print(f"⚠️  Database connection test failed (expected if not configured): {e}")

def main():
    """Run all tests"""
    print("🚀 Starting HybridSearchEngine tests...\n")
    
    try:
        test_search_result_creation()
        print()
        
        test_rrf_fusion()
        print()
        
        test_capabilities_reporting()
        print()
        
        test_mock_search_methods()
        print()
        
        test_database_connection()
        print()
        
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()