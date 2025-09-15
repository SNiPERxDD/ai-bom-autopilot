#!/usr/bin/env python3
"""
Test script for migration structure (without requiring DB connection)
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_migration_structure():
    """Test that migration modules can be imported and have required functions"""
    print("🧪 Testing Migration Structure")
    print("=" * 40)
    
    try:
        # Test 1: Import migration modules
        print("1. Testing module imports...")
        from core.db import migrations
        from core.db.connection import DatabaseManager
        print("   ✅ Migration modules imported successfully")
        
        # Test 2: Check required functions exist
        print("\n2. Checking required functions...")
        required_functions = [
            'run_migrations',
            'seed_policies', 
            'selftest',
            'test_fulltext_support',
            'migration_runner'
        ]
        
        for func_name in required_functions:
            if hasattr(migrations, func_name):
                print(f"   ✅ Function '{func_name}' exists")
            else:
                print(f"   ❌ Function '{func_name}' missing")
                return False
        
        # Test 3: Check global FTS_ENABLED flag
        print("\n3. Checking global flags...")
        if hasattr(migrations, 'FTS_ENABLED'):
            print(f"   ✅ FTS_ENABLED flag exists (value: {migrations.FTS_ENABLED})")
        else:
            print("   ❌ FTS_ENABLED flag missing")
            return False
        
        # Test 4: Check DatabaseManager class
        print("\n4. Checking DatabaseManager...")
        db_manager = DatabaseManager.__new__(DatabaseManager)  # Create without __init__
        required_methods = ['health_check', 'get_session']
        
        for method_name in required_methods:
            if hasattr(db_manager, method_name):
                print(f"   ✅ Method '{method_name}' exists")
            else:
                print(f"   ❌ Method '{method_name}' missing")
                return False
        
        # Test 5: Check __main__.py exists for CLI access
        print("\n5. Checking CLI entry point...")
        main_file = Path(__file__).parent / "core" / "db" / "__main__.py"
        if main_file.exists():
            print("   ✅ CLI entry point exists")
        else:
            print("   ❌ CLI entry point missing")
            return False
        
        print("\n" + "=" * 40)
        print("✅ All structure tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli_help():
    """Test that the CLI help works"""
    print("\n🔧 Testing CLI Interface")
    print("=" * 30)
    
    try:
        import subprocess
        import sys
        
        # Test help command
        result = subprocess.run([
            sys.executable, '-m', 'core.db.migrations', '--help'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ CLI help command works")
            print("📋 Available commands:")
            for line in result.stdout.split('\n'):
                if 'up' in line or 'selftest' in line:
                    print(f"   {line.strip()}")
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_migration_structure()
    if success:
        success = test_cli_help()
    
    if not success:
        sys.exit(1)
    
    print("\n🎉 All tests passed! Migration system is ready.")
    print("\n📖 Usage:")
    print("   python -m core.db.migrations up       # Run migrations")
    print("   python -m core.db.migrations selftest # Run diagnostics")