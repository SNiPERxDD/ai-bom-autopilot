#!/usr/bin/env python3
"""
Verification script for ML-BOM Autopilot foundation setup.
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are importable."""
    required_modules = [
        'fastapi',
        'uvicorn', 
        'langgraph',
        'pydantic',
        'git',  # gitpython
        'decouple',  # python-decouple
        'mysql.connector',  # mysql-connector-python
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            missing.append(module)
            print(f"✗ {module}")
    
    return missing

def check_project_structure():
    """Check if required directories exist."""
    required_dirs = [
        'apps',
        'core', 
        'infra',
        'seed',
        '.venv'
    ]
    
    missing = []
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✓ {dir_name}/")
        else:
            missing.append(dir_name)
            print(f"✗ {dir_name}/")
    
    return missing

def check_config_files():
    """Check if configuration files exist."""
    required_files = [
        'requirements.txt',
        '.env.example',
        '.env'
    ]
    
    missing = []
    for file_name in required_files:
        if Path(file_name).exists():
            print(f"✓ {file_name}")
        else:
            missing.append(file_name)
            print(f"✗ {file_name}")
    
    return missing

def main():
    """Run all verification checks."""
    print("ML-BOM Autopilot Foundation Setup Verification")
    print("=" * 50)
    
    print("\n1. Checking Dependencies:")
    missing_deps = check_dependencies()
    
    print("\n2. Checking Project Structure:")
    missing_dirs = check_project_structure()
    
    print("\n3. Checking Configuration Files:")
    missing_files = check_config_files()
    
    print("\n" + "=" * 50)
    
    if not missing_deps and not missing_dirs and not missing_files:
        print("✅ Foundation setup complete! All requirements satisfied.")
        return 0
    else:
        print("❌ Foundation setup incomplete:")
        if missing_deps:
            print(f"   Missing dependencies: {', '.join(missing_deps)}")
        if missing_dirs:
            print(f"   Missing directories: {', '.join(missing_dirs)}")
        if missing_files:
            print(f"   Missing files: {', '.join(missing_files)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())