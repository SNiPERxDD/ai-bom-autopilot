#!/usr/bin/env python3
"""
Test script for multi-provider embedding support
Tests Requirements 7.1, 7.2, and 7.4
"""

import os
import sys
import logging
import pytest
from decouple import config

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.embeddings.embedder import EmbeddingService

@pytest.fixture
def service():
    """Create an embedding service for tests"""
    return EmbeddingService()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_provider_initialization():
    """Test provider initialization and configuration validation"""
    print("🧪 Testing Embedding Provider Initialization")
    print("=" * 50)
    
    # Test current configuration
    try:
        service = EmbeddingService()
        print(f"✅ Service initialized successfully")
        
        # Get provider info
        info = service.get_provider_info()
        print(f"📊 Provider Info:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # Validate configuration
        validation = service.validate_provider_config()
        print(f"\n🔍 Configuration Validation:")
        print(f"   Valid: {validation['config_valid']}")
        
        if validation['warnings']:
            print(f"   Warnings:")
            for warning in validation['warnings']:
                print(f"     ⚠️  {warning}")
        
        if validation['errors']:
            print(f"   Errors:")
            for error in validation['errors']:
                print(f"     ❌ {error}")
        
        return service, validation['config_valid']
        
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return None, False

def test_embedding_generation(service):
    """Test embedding generation if service is available"""
    if not service:
        print("⏭️  Skipping embedding test - no service available")
        return
        
    print(f"\n🧪 Testing Embedding Generation")
    print("=" * 50)
    
    if not service._has_embedding_client():
        print("⏭️  Skipping embedding test - no valid API key configured")
        print("   Set OPENAI_API_KEY or GEMINI_API_KEY to test actual embedding generation")
        return
    
    test_texts = [
        "This is a test document for embedding generation.",
        "Machine learning models require proper governance and compliance."
    ]
    
    try:
        embeddings = service._get_embeddings(test_texts)
        print(f"✅ Generated {len(embeddings)} embeddings")
        print(f"   Dimensions: {len(embeddings[0]) if embeddings else 'N/A'}")
        print(f"   Expected: {service.dimensions}")
        
        # Verify dimensions match
        if embeddings and len(embeddings[0]) == service.dimensions:
            print(f"✅ Dimensions match configuration")
        else:
            print(f"❌ Dimension mismatch!")
        
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")

def test_provider_switching():
    """Test switching between providers"""
    print(f"\n🧪 Testing Provider Switching")
    print("=" * 50)
    
    original_provider = config('EMBED_PROVIDER', default='openai')
    original_dim = config('EMBEDDING_DIM', cast=int, default=1536)
    
    print(f"Current config: {original_provider} ({original_dim}D)")
    
    # Test configurations
    test_configs = [
        ('openai', 1536),
        ('gemini', 768)
    ]
    
    for provider, dimensions in test_configs:
        print(f"\n🔄 Testing {provider} with {dimensions} dimensions...")
        
        # Temporarily set environment variables
        os.environ['EMBED_PROVIDER'] = provider
        os.environ['EMBEDDING_DIM'] = str(dimensions)
        
        try:
            # Create new service instance
            service = EmbeddingService()
            info = service.get_provider_info()
            
            print(f"   Provider: {info['provider']}")
            print(f"   Dimensions: {info['dimensions']}")
            print(f"   Client Available: {info['client_available']}")
            print(f"   Status: {info['status']}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Restore original configuration
    os.environ['EMBED_PROVIDER'] = original_provider
    os.environ['EMBEDDING_DIM'] = str(original_dim)

def main():
    """Main test function"""
    print("🚀 Multi-Provider Embedding Test Suite")
    print("=" * 60)
    
    # Test 1: Provider initialization
    service, config_valid = test_provider_initialization()
    
    # Test 2: Embedding generation (if possible)
    if config_valid:
        test_embedding_generation(service)
    
    # Test 3: Provider switching
    test_provider_switching()
    
    print(f"\n✅ Test suite completed!")
    print(f"💡 To test with real API keys, set OPENAI_API_KEY or GEMINI_API_KEY")

if __name__ == "__main__":
    main()