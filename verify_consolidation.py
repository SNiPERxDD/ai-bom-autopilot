#!/usr/bin/env python3
"""
Verification script for repository consolidation and standardization
Ensures all components are properly organized and functional
"""

import os
import sys
import subprocess
from pathlib import Path

def check_directory_structure():
    """Verify the new directory structure is correct"""
    print("🔍 Checking directory structure...")
    
    required_dirs = [
        "apps/api",
        "apps/ui", 
        "core/bom",
        "core/db",
        "core/diff",
        "core/embeddings",
        "core/graph",
        "core/mcp_tools",
        "core/normalize",
        "core/policy",
        "core/scan_git",
        "core/scan_hf",
        "core/schemas",
        "core/search",
        "seed",
        "docs",
        "examples",
        "tests"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    print("✅ All required directories present")
    return True

def check_readme_files():
    """Verify README files exist in key directories"""
    print("📚 Checking README files...")
    
    readme_dirs = [
        ".",
        "apps",
        "core", 
        "seed",
        "docs",
        "examples",
        "tests"
    ]
    
    missing_readmes = []
    for dir_path in readme_dirs:
        readme_path = os.path.join(dir_path, "README.md")
        if not os.path.exists(readme_path):
            missing_readmes.append(readme_path)
    
    if missing_readmes:
        print(f"❌ Missing README files: {missing_readmes}")
        return False
    
    print("✅ All README files present")
    return True

def check_file_organization():
    """Verify files are properly organized"""
    print("📁 Checking file organization...")
    
    # Check that example files are in examples/
    example_files = [f for f in os.listdir(".") if f.startswith("example_")]
    if example_files:
        print(f"❌ Example files still in root: {example_files}")
        return False
    
    # Check that test files are in tests/
    test_files = [f for f in os.listdir(".") if f.startswith("test_")]
    if test_files:
        print(f"❌ Test files still in root: {test_files}")
        return False
    
    # Check that doc files are in docs/
    doc_files = [f for f in os.listdir(".") if f.endswith(".md") and f != "README.md"]
    if doc_files:
        print(f"❌ Documentation files still in root: {doc_files}")
        return False
    
    print("✅ Files properly organized")
    return True

def check_imports():
    """Verify imports still work after reorganization"""
    print("🔗 Checking imports...")
    
    try:
        # Test core imports
        from core.schemas.models import Project, Model, Dataset
        from core.db.connection import db_manager
        from core.embeddings.embedder import EmbeddingService
        from core.search.engine import HybridSearchEngine
        
        print("✅ Core imports working")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def check_test_structure():
    """Verify test structure is correct"""
    print("🧪 Checking test structure...")
    
    # Check that run_all_tests.py references correct paths
    with open("run_all_tests.py", "r") as f:
        content = f.read()
        
    if "tests/test_setup.py" not in content:
        print("❌ run_all_tests.py not updated for new structure")
        return False
    
    # Check that key test files exist
    key_tests = [
        "tests/test_setup.py",
        "tests/test_e2e_mock.py",
        "tests/test_sql_syntax.py"
    ]
    
    missing_tests = []
    for test_file in key_tests:
        if not os.path.exists(test_file):
            missing_tests.append(test_file)
    
    if missing_tests:
        print(f"❌ Missing test files: {missing_tests}")
        return False
    
    print("✅ Test structure correct")
    return True

def check_gitignore():
    """Verify .gitignore follows best practices"""
    print("🚫 Checking .gitignore...")
    
    with open(".gitignore", "r") as f:
        gitignore_content = f.read()
    
    required_patterns = [
        "__pycache__/",
        ".env",
        "*.log",
        ".DS_Store"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing .gitignore patterns: {missing_patterns}")
        return False
    
    print("✅ .gitignore follows best practices")
    return True

def check_documentation_quality():
    """Check that documentation is comprehensive"""
    print("📖 Checking documentation quality...")
    
    # Check main README has key sections
    with open("README.md", "r") as f:
        readme_content = f.read()
    
    required_sections = [
        "Quick Start",
        "Architecture Overview", 
        "Environment Setup",
        "Project Structure",
        "Troubleshooting"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in readme_content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ Missing README sections: {missing_sections}")
        return False
    
    # Check for mermaid diagram
    if "```mermaid" not in readme_content:
        print("❌ Missing architecture diagram")
        return False
    
    print("✅ Documentation is comprehensive")
    return True

def main():
    """Run all verification checks"""
    print("🚀 AI-BOM Autopilot Repository Consolidation Verification")
    print("=" * 60)
    
    checks = [
        ("Directory Structure", check_directory_structure),
        ("README Files", check_readme_files),
        ("File Organization", check_file_organization),
        ("Import Structure", check_imports),
        ("Test Structure", check_test_structure),
        ("GitIgnore", check_gitignore),
        ("Documentation Quality", check_documentation_quality)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with error: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📈 Results: {passed}/{total} checks passed")
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {check_name}")
    
    if passed == total:
        print("\n🎉 Repository consolidation successful!")
        print("✅ All checks passed - repository is properly organized")
        print("\n📝 Next steps:")
        print("  1. Commit the consolidated structure")
        print("  2. Update any CI/CD pipelines")
        print("  3. Notify team of new structure")
        return True
    else:
        print(f"\n❌ {total - passed} checks failed")
        print("🔧 Please fix the failing checks before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)