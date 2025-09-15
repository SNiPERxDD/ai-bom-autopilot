#!/usr/bin/env python3
"""
Integration test for the embedding service with database
"""

import os
import sys
import logging
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.embeddings.embedder import EmbeddingService
from core.schemas.models import EvidenceChunk, RefType, ScanState, Project

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_store_chunks_mock():
    """Test storing chunks with mocked database"""
    print("Testing chunk storage with mocked database...")
    
    # Mock database session
    mock_session = MagicMock()
    mock_session.execute.return_value = None
    mock_session.commit.return_value = None
    
    # Mock database manager
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': True, 'fulltext': False}
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        
        service = EmbeddingService()
        
        # Create test chunks
        chunks = [
            EvidenceChunk(
                project_id=1,
                ref_type=RefType.FILE,
                ref_path="test.py",
                commit_sha="abc123",
                chunk_ix=0,
                text="This is a test chunk",
                token_count=5,
                emb=[0.1, 0.2, 0.3],
                meta={"test": True}
            ),
            EvidenceChunk(
                project_id=1,
                ref_type=RefType.CONFIG,
                ref_path="config.yaml",
                commit_sha="abc123",
                chunk_ix=0,
                text="Another test chunk",
                token_count=4,
                meta={"config": True}
            )
        ]
        
        # Test storing chunks
        service._store_chunks(chunks)
        
        # Verify database calls were made
        assert mock_session.execute.called, "Should call database execute"
        assert mock_session.commit.called, "Should commit transaction"
        
        print("✓ Chunk storage working correctly")

def test_process_evidence_mock():
    """Test the full evidence processing pipeline with mocks"""
    print("Testing evidence processing pipeline...")
    
    # Mock database session
    mock_session = MagicMock()
    mock_session.execute.return_value = None
    mock_session.commit.return_value = None
    
    # Mock database manager
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': False, 'fulltext': False}  # No vector support for this test
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        
        service = EmbeddingService()
        
        # Create test state
        project = Project(id=1, name="test", repo_url="https://github.com/test/repo")
        state = ScanState(
            project=project,
            commit_sha="abc123",
            files=["test.py", "README.md"]
        )
        
        # Mock file reading
        test_content = "This is test file content that should be chunked properly."
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = test_content
            
            # Process evidence
            result_state = service.process_evidence(state)
            
            # Verify results
            assert result_state.evidence_chunks, "Should create evidence chunks"
            assert len(result_state.evidence_chunks) >= len(state.files), "Should have chunks for each file"
            
            print(f"✓ Created {len(result_state.evidence_chunks)} evidence chunks")

def test_search_functionality_mock():
    """Test search functionality with mocked database"""
    print("Testing search functionality...")
    
    # Mock search results
    mock_results = [
        MagicMock(_mapping={'id': 1, 'text': 'test result 1', 'ref_path': 'test1.py'}),
        MagicMock(_mapping={'id': 2, 'text': 'test result 2', 'ref_path': 'test2.py'})
    ]
    
    mock_session = MagicMock()
    mock_session.execute.return_value = mock_results
    
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': False, 'fulltext': False}
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        
        service = EmbeddingService()
        
        # Test fallback search
        results = service._fallback_search(project_id=1, query="test", limit=10)
        
        assert len(results) == 2, "Should return mocked results"
        assert results[0]['id'] == 1, "Should return correct result data"
        
        print("✓ Search functionality working correctly")

if __name__ == "__main__":
    print("Running embedding service integration tests...")
    
    try:
        test_store_chunks_mock()
        test_process_evidence_mock()
        test_search_functionality_mock()
        
        print("\n✅ All integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)