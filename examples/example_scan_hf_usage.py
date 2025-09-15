#!/usr/bin/env python3
"""Example usage of the HuggingFace scanner."""

import os
import sys
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.scan_hf.fetcher import HuggingFaceFetcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Demonstrate HuggingFace scanner usage"""
    logger.info("HuggingFace Scanner Usage Example")
    logger.info("=" * 40)
    
    # Initialize fetcher with custom TTL
    fetcher = HuggingFaceFetcher(cache_ttl_hours=12)
    
    # Example 1: Fetch a single model card
    logger.info("\n1. Fetching a single model card...")
    card = fetcher.fetch_card("gpt2")
    if card:
        logger.info(f"Model: {card.slug}")
        logger.info(f"Type: {card.type}")
        logger.info(f"License: {card.license}")
        logger.info(f"Pipeline: {card.pipeline_tag}")
        logger.info(f"Tags: {', '.join(card.tags[:5])}...")  # First 5 tags
        logger.info(f"Version: {card.version}")
    
    # Example 2: Fetch with specific version
    logger.info("\n2. Fetching with specific version...")
    versioned_card = fetcher.fetch_card("gpt2", version="main")
    if versioned_card:
        logger.info(f"Versioned fetch: {versioned_card.slug} @ {versioned_card.version}")
    
    # Example 3: Batch fetch multiple cards
    logger.info("\n3. Batch fetching multiple cards...")
    models = [
        "bert-base-uncased",
        "distilbert-base-uncased",
        "microsoft/DialoGPT-small"
    ]
    
    results = fetcher.batch_fetch_cards(models)
    for slug, card in results.items():
        logger.info(f"  {slug}: {card.type}, license: {card.license}")
    
    # Example 4: Cache statistics
    logger.info("\n4. Cache statistics...")
    stats = fetcher.get_cache_stats()
    logger.info(f"Total entries: {stats['total_entries']}")
    logger.info(f"Active entries: {stats['active_entries']}")
    logger.info(f"Expired entries: {stats['expired_entries']}")
    logger.info(f"Cache TTL: {stats['cache_ttl_hours']} hours")
    
    # Example 5: Clear expired cache
    logger.info("\n5. Cache management...")
    cleared = fetcher.clear_expired_cache()
    logger.info(f"Cleared {cleared} expired entries")
    
    # Example 6: Validate slugs
    logger.info("\n6. Slug validation...")
    test_slugs = [
        "microsoft/DialoGPT-medium",  # Valid
        "invalid-slug",               # Invalid
        "user/repo-name_v2.0"        # Valid
    ]
    
    for slug in test_slugs:
        is_valid = fetcher.validate_slug(slug)
        logger.info(f"  {slug}: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    logger.info("\n" + "=" * 40)
    logger.info("Example completed!")

if __name__ == "__main__":
    main()