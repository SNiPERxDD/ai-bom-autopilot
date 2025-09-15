#!/usr/bin/env python3
"""
Example: Vector Column Migration Usage

This script demonstrates how to use the vector column migration functionality
to switch between different embedding providers.
"""

import os
import sys
from decouple import config

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def example_openai_to_gemini_migration():
    """Example: Migrate from OpenAI (1536D) to Gemini (768D)"""
    print("📝 Example: Migrating from OpenAI to Gemini")
    print("=" * 50)
    
    # Step 1: Check current status
    print("1. Checking current vector column status...")
    from core.db.resize_vector_migration import get_current_vector_dimension, check_table_exists
    
    if not check_table_exists():
        print("❌ evidence_chunks table not found. Run migrations first:")
        print("   python -m core.db.migrations up")
        return False
    
    current_dim = get_current_vector_dimension()
    if current_dim:
        print(f"   Current dimension: {current_dim}")
    else:
        print("❌ Could not determine current dimension")
        return False
    
    # Step 2: Update environment configuration
    print("\n2. Update your environment configuration:")
    print("   # Change from OpenAI to Gemini")
    print("   EMBED_PROVIDER=gemini")
    print("   EMBEDDING_DIM=768")
    print("   GEMINI_API_KEY=your-gemini-key")
    print("   # Comment out OpenAI config")
    print("   # OPENAI_API_KEY=...")
    
    # Step 3: Run migration
    print("\n3. Run the migration:")
    print("   python -m core.db.migrations resize-vector")
    print("   # Or with explicit dimension:")
    print("   python -m core.db.migrations resize-vector --dimension 768")
    
    # Step 4: Re-embed existing data
    print("\n4. Re-embed existing data (if any):")
    print("   # The migration clears vector data during resize")
    print("   # You'll need to re-run embedding for existing chunks")
    print("   # This ensures all vectors use the new provider's dimensions")
    
    return True

def example_gemini_to_openai_migration():
    """Example: Migrate from Gemini (768D) to OpenAI (1536D)"""
    print("📝 Example: Migrating from Gemini to OpenAI")
    print("=" * 50)
    
    print("1. Update your environment configuration:")
    print("   # Change from Gemini to OpenAI")
    print("   EMBED_PROVIDER=openai")
    print("   EMBEDDING_DIM=1536")
    print("   OPENAI_API_KEY=sk-your-openai-key")
    print("   # Comment out Gemini config")
    print("   # GEMINI_API_KEY=...")
    
    print("\n2. Run the migration:")
    print("   python -m core.db.migrations resize-vector")
    
    print("\n3. Verify the migration:")
    print("   python -m core.db.resize_vector_migration status")

def example_check_migration_status():
    """Example: Check current migration status"""
    print("📝 Example: Checking Migration Status")
    print("=" * 50)
    
    try:
        from core.db.resize_vector_migration import (
            get_current_vector_dimension, 
            check_table_exists,
            check_vector_support,
            get_row_count
        )
        
        # Check table existence
        if not check_table_exists():
            print("❌ evidence_chunks table does not exist")
            print("   Run: python -m core.db.migrations up")
            return False
        
        # Check vector support
        if not check_vector_support():
            print("❌ Vector functions not supported in this TiDB instance")
            return False
        
        # Get current dimension
        current_dim = get_current_vector_dimension()
        if current_dim:
            print(f"✅ Current vector dimension: {current_dim}")
        else:
            print("❌ Could not determine vector dimension")
            return False
        
        # Get row count
        try:
            row_count = get_row_count()
            print(f"📊 Rows in evidence_chunks: {row_count}")
        except Exception as e:
            print(f"⚠️  Could not get row count: {e}")
        
        # Show current configuration
        provider = config('EMBED_PROVIDER', default='openai')
        embedding_dim = config('EMBEDDING_DIM', cast=int, default=None)
        print(f"🔧 Current provider: {provider}")
        print(f"🔧 Configured dimension: {embedding_dim}")
        
        # Check for mismatch
        if embedding_dim and current_dim != embedding_dim:
            print(f"⚠️  Dimension mismatch!")
            print(f"   Database has {current_dim}D, config expects {embedding_dim}D")
            print(f"   Run migration: python -m core.db.migrations resize-vector")
        else:
            print("✅ Configuration matches database schema")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

def main():
    """Main example runner"""
    print("🚀 ML-BOM Autopilot Vector Migration Examples")
    print("=" * 60)
    
    examples = [
        ("Check Migration Status", example_check_migration_status),
        ("OpenAI to Gemini Migration", example_openai_to_gemini_migration),
        ("Gemini to OpenAI Migration", example_gemini_to_openai_migration),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n{i}. {name}")
        print("-" * 40)
        try:
            func()
        except Exception as e:
            print(f"❌ Example failed: {e}")
        
        if i < len(examples):
            print("\n" + "=" * 60)
    
    print("\n🎯 Key Points:")
    print("- Always backup your data before migration")
    print("- Vector data is cleared during resize (TiDB requirement)")
    print("- Re-embed existing chunks after provider switch")
    print("- Use 'status' command to check current configuration")
    print("- Migration is transactional and safe to retry")

if __name__ == "__main__":
    main()