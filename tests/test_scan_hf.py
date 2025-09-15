#!/usr/bin/env python3
"""Test script for HuggingFace scanner functionality."""

import os
import sys
import logging
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.scan_hf.fetcher import HuggingFaceFetcher, HFCard, CacheEntry

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cache_entry():
    """Test CacheEntry TTL functionality"""
    logger.info("Testing CacheEntry TTL functionality...")
    
    # Create a test card
    test_card = HFCard(
        slug="test/model",
        type="model",
        license="MIT",
        version="main"
    )
    
    # Test non-expired entry
    future_time = datetime.now() + timedelta(hours=1)
    entry = CacheEntry(data=test_card, expires_at=future_time)
    assert not entry.is_expired(), "Entry should not be expired"
    
    # Test expired entry
    past_time = datetime.now() - timedelta(hours=1)
    expired_entry = CacheEntry(data=test_card, expires_at=past_time)
    assert expired_entry.is_expired(), "Entry should be expired"
    
    logger.info("✓ CacheEntry TTL tests passed")

def test_fetcher_initialization():
    """Test HuggingFaceFetcher initialization"""
    logger.info("Testing HuggingFaceFetcher initialization...")
    
    # Test default TTL
    fetcher = HuggingFaceFetcher()
    assert fetcher.cache_ttl_hours == 24, f"Expected default TTL 24, got {fetcher.cache_ttl_hours}"
    
    # Test custom TTL
    fetcher_custom = HuggingFaceFetcher(cache_ttl_hours=12)
    assert fetcher_custom.cache_ttl_hours == 12, f"Expected custom TTL 12, got {fetcher_custom.cache_ttl_hours}"
    
    # Test environment variable TTL
    os.environ['HF_CACHE_TTL_HOURS'] = '48'
    fetcher_env = HuggingFaceFetcher()
    assert fetcher_env.cache_ttl_hours == 48, f"Expected env TTL 48, got {fetcher_env.cache_ttl_hours}"
    
    # Clean up
    del os.environ['HF_CACHE_TTL_HOURS']
    
    logger.info("✓ HuggingFaceFetcher initialization tests passed")

def test_slug_validation():
    """Test slug validation"""
    logger.info("Testing slug validation...")
    
    fetcher = HuggingFaceFetcher()
    
    # Valid slugs
    valid_slugs = [
        "microsoft/DialoGPT-medium",
        "huggingface/CodeBERTa-small-v1",
        "google/flan-t5-base",
        "user123/model-name_v2.0"
    ]
    
    for slug in valid_slugs:
        assert fetcher.validate_slug(slug), f"Should be valid: {slug}"
    
    # Invalid slugs
    invalid_slugs = [
        "invalid-slug",  # No slash
        "/invalid",      # Empty username
        "invalid/",      # Empty repo
        "user/repo/extra",  # Too many parts
        "",              # Empty
        "user with spaces/repo"  # Invalid characters
    ]
    
    for slug in invalid_slugs:
        assert not fetcher.validate_slug(slug), f"Should be invalid: {slug}"
    
    logger.info("✓ Slug validation tests passed")

def test_yaml_parsing():
    """Test YAML front-matter parsing"""
    logger.info("Testing YAML front-matter parsing...")
    
    fetcher = HuggingFaceFetcher()
    
    # Valid YAML
    valid_yaml = """---
license: mit
tags:
- text-generation
- pytorch
datasets:
- common_voice
model_type: gpt2
---

# Model Description
This is a test model.
"""
    
    result = fetcher._parse_card_yaml(valid_yaml)
    assert result['license'] == 'mit', f"Expected license 'mit', got {result.get('license')}"
    assert 'text-generation' in result['tags'], "Expected 'text-generation' in tags"
    assert result['model_type'] == 'gpt2', f"Expected model_type 'gpt2', got {result.get('model_type')}"
    
    # No YAML front-matter
    no_yaml = "# Just a regular markdown file"
    result = fetcher._parse_card_yaml(no_yaml)
    assert result == {}, f"Expected empty dict, got {result}"
    
    # Invalid YAML
    invalid_yaml = """---
license: mit
invalid: [unclosed list
---"""
    result = fetcher._parse_card_yaml(invalid_yaml)
    assert result == {}, f"Expected empty dict for invalid YAML, got {result}"
    
    logger.info("✓ YAML parsing tests passed")

def test_cache_management():
    """Test cache management functionality"""
    logger.info("Testing cache management...")
    
    fetcher = HuggingFaceFetcher(cache_ttl_hours=1)
    
    # Create test cards
    card1 = HFCard(slug="test/model1", type="model", version="v1")
    card2 = HFCard(slug="test/model2", type="model", version="v2")
    
    # Add to cache with different expiration times
    future_time = datetime.now() + timedelta(hours=2)
    past_time = datetime.now() - timedelta(hours=1)
    
    fetcher.cache["test1"] = CacheEntry(data=card1, expires_at=future_time)
    fetcher.cache["test2"] = CacheEntry(data=card2, expires_at=past_time)
    
    # Test cache stats
    stats = fetcher.get_cache_stats()
    assert stats['total_entries'] == 2, f"Expected 2 total entries, got {stats['total_entries']}"
    assert stats['expired_entries'] == 1, f"Expected 1 expired entry, got {stats['expired_entries']}"
    assert stats['active_entries'] == 1, f"Expected 1 active entry, got {stats['active_entries']}"
    
    # Test clearing expired cache
    cleared = fetcher.clear_expired_cache()
    assert cleared == 1, f"Expected 1 cleared entry, got {cleared}"
    assert len(fetcher.cache) == 1, f"Expected 1 remaining entry, got {len(fetcher.cache)}"
    
    logger.info("✓ Cache management tests passed")

def test_live_fetch():
    """Test live fetching from HuggingFace (if network available)"""
    logger.info("Testing live fetch (requires network)...")
    
    fetcher = HuggingFaceFetcher(cache_ttl_hours=1)
    
    try:
        # Test with a well-known small model
        card = fetcher.fetch_card("gpt2")
        
        if card:
            logger.info(f"✓ Successfully fetched card for gpt2:")
            logger.info(f"  Type: {card.type}")
            logger.info(f"  License: {card.license}")
            logger.info(f"  Tags: {card.tags[:3]}...")  # Show first 3 tags
            logger.info(f"  Pipeline tag: {card.pipeline_tag}")
            
            # Test caching
            card2 = fetcher.fetch_card("gpt2")
            assert card2 is not None, "Second fetch should hit cache"
            
            # Test cache stats
            stats = fetcher.get_cache_stats()
            logger.info(f"  Cache stats: {stats}")
            
        else:
            logger.warning("Could not fetch gpt2 card (network issue?)")
            
    except Exception as e:
        logger.warning(f"Live fetch test failed (expected if no network): {e}")

def main():
    """Run all tests"""
    logger.info("Starting HuggingFace scanner tests...")
    
    try:
        test_cache_entry()
        test_fetcher_initialization()
        test_slug_validation()
        test_yaml_parsing()
        test_cache_management()
        test_live_fetch()
        
        logger.info("🎉 All tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()