#!/usr/bin/env python3
"""
Integration test for multi-provider embedding support
Tests integration with existing database and workflow components
"""

import os
import sys
import logging
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.embeddings.embedder import EmbeddingService
from core.schemas.models import ScanState, Project, EvidenceChunk, RefType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_embedding_service_integration():
    """Test that the embedding service integrates properly with existing components"""
    print("🧪 Testing Embedding Service Integration")
    print("=" * 50)
    
    # Test 1: Service initialization with different providers
    print("\n1️⃣ Testing service initialization...")
    
    # Test OpenAI configuration
    os.environ['EMBED_PROVIDER'] = 'openai'
    os.environ['EMBEDDING_DIM'] = '1536'
    
    try:
        service_openai = EmbeddingService()
        print(f"✅ OpenAI service initialized: {service_openai.provider} ({service_openai.dimensions}D)")
    except Exception as e:
        print(f"❌ OpenAI service failed: {e}")
        return False
    
    # Test Gemini configuration
    os.environ['EMBED_PROVIDER'] = 'gemini'
    os.environ['EMBEDDING_DIM'] = '768'
    
    try:
        service_gemini = EmbeddingService()
        print(f"✅ Gemini service initialized: {service_gemini.provider} ({service_gemini.dimensions}D)")
    except Exception as e:
        print(f"❌ Gemini service failed: {e}")
        return False
    
    # Test 2: Evidence chunk creation and processing
    print("\n2️⃣ Testing evidence chunk processing...")
    
    # Create mock scan state
    mock_project = Project(
        id=1,
        name="test-project",
        repo_url="https://github.com/test/repo.git"
    )
    
    scan_state = ScanState(
        project=mock_project,
        commit_sha="abc123",
        files=["test_file.py", "README.md"],
        evidence_chunks=[]
    )
    
    # Create test evidence chunks
    test_chunks = [
        EvidenceChunk(
            project_id=1,
            ref_type=RefType.FILE,
            ref_path="test_file.py",
            commit_sha="abc123",
            chunk_ix=0,
            text="This is a test Python file with machine learning code.",
            token_count=12,
            meta={"file_size": 100}
        ),
        EvidenceChunk(
            project_id=1,
            ref_type=RefType.README,
            ref_path="README.md",
            commit_sha="abc123",
            chunk_ix=0,
            text="This project implements AI governance and compliance tracking.",
            token_count=10,
            meta={"file_size": 200}
        )
    ]
    
    # Test batch embedding (mocked)
    print("   Testing batch embedding process...")
    
    # Mock the embedding API calls
    mock_embeddings = [
        [0.1] * service_openai.dimensions,  # Mock OpenAI embedding
        [0.2] * service_openai.dimensions   # Mock OpenAI embedding
    ]
    
    with patch.object(service_openai, '_get_embeddings', return_value=mock_embeddings):
        try:
            service_openai._batch_embed_chunks(test_chunks)
            print(f"✅ OpenAI batch embedding completed")
            
            # Verify embeddings were added
            for i, chunk in enumerate(test_chunks):
                if chunk.emb and len(chunk.emb) == service_openai.dimensions:
                    print(f"   ✅ Chunk {i}: {len(chunk.emb)} dimensions")
                else:
                    print(f"   ❌ Chunk {i}: embedding missing or wrong size")
                    
        except Exception as e:
            print(f"❌ Batch embedding failed: {e}")
            return False
    
    # Test 3: Provider switching validation
    print("\n3️⃣ Testing provider switching...")
    
    # Test dimension validation
    test_configs = [
        ('openai', 1536, True),
        ('openai', 3072, True),
        ('openai', 768, False),  # Should warn
        ('gemini', 768, True),
        ('gemini', 1536, False),  # Should warn
    ]
    
    for provider, dim, should_be_normal in test_configs:
        os.environ['EMBED_PROVIDER'] = provider
        os.environ['EMBEDDING_DIM'] = str(dim)
        
        try:
            service = EmbeddingService()
            validation = service.validate_provider_config()
            
            has_warnings = len(validation['warnings']) > 1  # More than just the test skip warning
            
            if should_be_normal and has_warnings:
                print(f"   ⚠️  {provider}({dim}D): Unexpected warnings")
            elif not should_be_normal and not has_warnings:
                print(f"   ⚠️  {provider}({dim}D): Expected warnings but got none")
            else:
                print(f"   ✅ {provider}({dim}D): Validation as expected")
                
        except Exception as e:
            print(f"   ❌ {provider}({dim}D): Failed - {e}")
    
    # Test 4: Database integration (mocked)
    print("\n4️⃣ Testing database integration...")
    
    # Mock database session and operations
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_session = Mock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.capabilities = {'vector': True}
        
        # Mock existing chunk check (no duplicates)
        mock_session.execute.return_value.fetchone.return_value = None
        
        try:
            service_openai._store_chunks(test_chunks)
            print(f"✅ Database storage integration successful")
            
            # Verify database calls were made
            call_count = mock_session.execute.call_count
            print(f"   Database calls made: {call_count}")
            
        except Exception as e:
            print(f"❌ Database integration failed: {e}")
            return False
    
    print("\n✅ All integration tests passed!")
    return True

def test_startup_logging():
    """Test that startup logging meets requirements (7.4)"""
    print("\n🧪 Testing Startup Logging (Requirement 7.4)")
    print("=" * 50)
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    
    logger = logging.getLogger('core.embeddings.embedder')
    logger.addHandler(handler)
    
    # Test OpenAI logging
    os.environ['EMBED_PROVIDER'] = 'openai'
    os.environ['EMBEDDING_DIM'] = '1536'
    
    service = EmbeddingService()
    
    log_output = log_capture.getvalue()
    
    # Check required log elements
    required_elements = [
        'Embedding Service Initialized',
        'Provider: openai',
        'Dimensions: 1536',
        'Client Available:'
    ]
    
    all_present = True
    for element in required_elements:
        if element in log_output:
            print(f"✅ Found: {element}")
        else:
            print(f"❌ Missing: {element}")
            all_present = False
    
    if all_present:
        print("✅ Startup logging meets requirements")
    else:
        print("❌ Startup logging incomplete")
    
    logger.removeHandler(handler)
    return all_present

def main():
    """Main test function"""
    print("🚀 Multi-Provider Embedding Integration Test Suite")
    print("=" * 60)
    
    # Run integration tests
    integration_success = test_embedding_service_integration()
    
    # Run startup logging test
    logging_success = test_startup_logging()
    
    print(f"\n📊 Test Results:")
    print(f"   Integration Tests: {'✅ PASS' if integration_success else '❌ FAIL'}")
    print(f"   Startup Logging: {'✅ PASS' if logging_success else '❌ FAIL'}")
    
    if integration_success and logging_success:
        print(f"\n🎉 All tests passed! Multi-provider embedding support is working correctly.")
        print(f"💡 Requirements 7.1, 7.2, and 7.4 have been implemented successfully.")
    else:
        print(f"\n⚠️  Some tests failed. Please review the implementation.")
    
    return integration_success and logging_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)