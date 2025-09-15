#!/usr/bin/env python3
"""
Test setup script to verify all components work
"""

import sys
import os
import subprocess

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def test_imports():
    """Test all critical imports"""
    print("🔍 Testing imports...")
    
    imports_to_test = [
        "pydantic",
        "fastapi", 
        "sqlalchemy",
        "requests",
        "yaml",
        "json",
        "hashlib",
        "datetime"
    ]
    
    for module in imports_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            return False
    
    return True

def test_core_imports():
    """Test our core module imports"""
    print("🔍 Testing core module imports...")
    
    # Add current directory to Python path
    sys.path.insert(0, os.getcwd())
    
    try:
        from core.schemas.models import Project, ScanState
        print("  ✅ core.schemas.models")
    except Exception as e:
        print(f"  ❌ core.schemas.models: {e}")
        return False
    
    return True

def create_mock_env():
    """Create mock environment file for testing"""
    print("🔧 Creating mock environment...")
    
    mock_env = """# Mock environment for testing
TIDB_URL=mysql+pymysql://test:test@localhost:3306/test
DB_USER=test
DB_PASS=test
DB_NAME=test
OPENAI_API_KEY=sk-test
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
SLACK_WEBHOOK_URL=https://hooks.slack.com/test
DEBUG=true
LOG_LEVEL=INFO
"""
    
    with open('.env', 'w') as f:
        f.write(mock_env)
    
    print("✅ Mock .env created")
    return True

def main():
    """Run all tests"""
    print("🚀 Starting AI-BOM Autopilot setup test...\n")
    
    steps = [
        ("Install Dependencies", install_dependencies),
        ("Test Basic Imports", test_imports),
        ("Create Mock Environment", create_mock_env),
        ("Test Core Imports", test_core_imports),
    ]
    
    for step_name, step_func in steps:
        print(f"\n=== {step_name} ===")
        if not step_func():
            print(f"❌ {step_name} failed!")
            return False
        print(f"✅ {step_name} passed!")
    
    print("\n🎉 All setup tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)