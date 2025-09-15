#!/usr/bin/env python3
"""
Test script for database migrations
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.db.migrations import run_migrations, seed_policies, selftest, test_fulltext_support
from core.db.connection import db_manager

def test_migrations():
    """Test the migration system"""
    print("🧪 Testing ML-BOM Autopilot Migration System")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        # Test 1: Database connection
        print("1. Testing database connection...")
        health = db_manager.health_check()
        if health["status"] != "healthy":
            print(f"❌ Database connection failed: {health.get('error')}")
            return False
        print("✅ Database connection successful")
        
        # Test 2: FULLTEXT support detection
        print("\n2. Testing FULLTEXT support detection...")
        fts_supported = test_fulltext_support()
        if fts_supported:
            print("✅ FULLTEXT support detected")
        else:
            print("🟡 FULLTEXT not supported, will use BM25 fallback")
        
        # Test 3: Run migrations
        print("\n3. Running database migrations...")
        run_migrations()
        print("✅ Migrations completed successfully")
        
        # Test 4: Seed policies
        print("\n4. Seeding default policies...")
        seed_policies()
        print("✅ Policies seeded successfully")
        
        # Test 5: Verify tables exist
        print("\n5. Verifying table creation...")
        expected_tables = [
            'projects', 'models', 'datasets', 'prompts', 'prompt_blobs', 
            'tools', 'boms', 'bom_diffs', 'policies', 'policy_overrides',
            'policy_events', 'suppressions', 'actions', 'evidence_chunks'
        ]
        
        with db_manager.engine.connect() as conn:
            from sqlalchemy import text
            for table in expected_tables:
                result = conn.execute(text(f"SHOW TABLES LIKE '{table}'"))
                if result.fetchone():
                    print(f"   ✅ Table '{table}' exists")
                else:
                    print(f"   ❌ Table '{table}' missing")
                    return False
        
        print("\n" + "=" * 50)
        print("✅ All migration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_migrations()
    if not success:
        sys.exit(1)
    
    print("\n🔍 Running comprehensive self-test...")
    selftest()