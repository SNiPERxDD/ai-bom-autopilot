#!/usr/bin/env python3
"""Integration test for HuggingFace scanner with caching demonstration."""

import os
import sys
import logging
import time
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.scan_hf.fetcher import HuggingFaceFetcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_caching_behavior():
    """Test TTL-based caching behavior with real API calls"""
    logger.info("Testing caching behavior with real HuggingFace API...")
    
    # Use short TTL for testing
    fetcher = HuggingFaceFetcher(cache_ttl_hours=1)
    
    # Test models and datasets
    test_items = [
        "gpt2",  # Popular model
        "microsoft/DialoGPT-small",  # Another model
    ]
    
    logger.info("First fetch (should hit API)...")
    start_time = time.time()
    
    results = {}
    for item in test_items:
        logger.info(f"Fetching {item}...")
        card = fetcher.fetch_card(item)
        if card:
            results[item] = card
            logger.info(f"  ✓ {item}: {card.type}, license: {card.license}")
        else:
            logger.warning(f"  ✗ Failed to fetch {item}")
    
    first_fetch_time = time.time() - start_time
    logger.info(f"First fetch took {first_fetch_time:.2f}s")
    
    # Check cache stats
    stats = fetcher.get_cache_stats()
    logger.info(f"Cache stats after first fetch: {stats}")
    
    logger.info("\nSecond fetch (should hit cache)...")
    start_time = time.time()
    
    cached_results = {}
    for item in test_items:
        card = fetcher.fetch_card(item)
        if card:
            cached_results[item] = card
    
    second_fetch_time = time.time() - start_time
    logger.info(f"Second fetch took {second_fetch_time:.2f}s")
    
    # Verify caching worked (should be much faster)
    if second_fetch_time < first_fetch_time * 0.1:  # Should be at least 10x faster
        logger.info("✓ Caching is working effectively!")
    else:
        logger.warning(f"⚠ Caching may not be working as expected (times: {first_fetch_time:.2f}s vs {second_fetch_time:.2f}s)")
    
    # Verify data consistency
    for item in test_items:
        if item in results and item in cached_results:
            original = results[item]
            cached = cached_results[item]
            if original.slug == cached.slug and original.license == cached.license:
                logger.info(f"✓ Data consistency verified for {item}")
            else:
                logger.error(f"✗ Data inconsistency for {item}")

def test_batch_fetching():
    """Test batch fetching with rate limiting"""
    logger.info("\nTesting batch fetching...")
    
    fetcher = HuggingFaceFetcher(cache_ttl_hours=1)
    
    # Test with a small batch
    test_slugs = [
        "gpt2",
        "bert-base-uncased",
        "distilbert-base-uncased"
    ]
    
    logger.info(f"Batch fetching {len(test_slugs)} items...")
    start_time = time.time()
    
    results = fetcher.batch_fetch_cards(test_slugs)
    
    batch_time = time.time() - start_time
    logger.info(f"Batch fetch completed in {batch_time:.2f}s")
    logger.info(f"Successfully fetched {len(results)}/{len(test_slugs)} cards")
    
    for slug, card in results.items():
        logger.info(f"  ✓ {slug}: {card.type}, {card.license}")

def test_version_support():
    """Test version/revision support"""
    logger.info("\nTesting version support...")
    
    fetcher = HuggingFaceFetcher(cache_ttl_hours=1)
    
    # Test with and without version
    slug = "gpt2"
    
    # Fetch without version
    card_main = fetcher.fetch_card(slug)
    if card_main:
        logger.info(f"✓ Fetched {slug} (main): version={card_main.version}")
    
    # Fetch with specific version (if available)
    card_versioned = fetcher.fetch_card(slug, version="main")
    if card_versioned:
        logger.info(f"✓ Fetched {slug} (main): version={card_versioned.version}")
    
    # Check that they're cached separately
    stats = fetcher.get_cache_stats()
    logger.info(f"Cache entries after version test: {stats['total_entries']}")

def test_error_handling():
    """Test error handling for invalid slugs"""
    logger.info("\nTesting error handling...")
    
    fetcher = HuggingFaceFetcher(cache_ttl_hours=1)
    
    # Test invalid slugs
    invalid_slugs = [
        "nonexistent/model-that-does-not-exist",
        "invalid-slug-format",
        ""
    ]
    
    for slug in invalid_slugs:
        logger.info(f"Testing invalid slug: '{slug}'")
        card = fetcher.fetch_card(slug)
        if card is None:
            logger.info(f"  ✓ Correctly handled invalid slug: {slug}")
        else:
            logger.warning(f"  ⚠ Unexpected success for invalid slug: {slug}")

def main():
    """Run integration tests"""
    logger.info("Starting HuggingFace scanner integration tests...")
    logger.info("Note: These tests require network access to HuggingFace API")
    
    try:
        test_caching_behavior()
        test_batch_fetching()
        test_version_support()
        test_error_handling()
        
        logger.info("\n🎉 All integration tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()