#!/usr/bin/env python3
"""
Test script to verify seed data functionality
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_sample_project_structure():
    """Test that sample project has expected structure"""
    print("Testing sample project structure...")
    
    sample_project = Path("seed/sample_project")
    
    required_files = [
        "README.md",
        "requirements.txt", 
        "pyproject.toml",
        "config.yaml",
        "train.py",
        "data_processing.py",
        "evaluation.py",
        "notebook.ipynb",
        "models/model_config.json",
        "datasets/dataset_manifest.yaml",
        "prompts/system_prompt.txt",
        "prompts/classification_prompt.txt", 
        "prompts/qa_prompt.txt",
        "tools/requirements.txt",
        "tools/model_utils.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = sample_project / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print(f"✅ All {len(required_files)} required files present")
        return True

def test_model_config():
    """Test model configuration file"""
    print("Testing model configuration...")
    
    config_path = Path("seed/sample_project/models/model_config.json")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        models = config.get("models", [])
        if len(models) < 4:
            print(f"❌ Expected at least 4 models, found {len(models)}")
            return False
        
        required_fields = ["name", "type", "license", "provider", "version"]
        for model in models:
            for field in required_fields:
                if field not in model:
                    print(f"❌ Model missing field '{field}': {model.get('name', 'unknown')}")
                    return False
        
        print(f"✅ Model config valid with {len(models)} models")
        return True
        
    except Exception as e:
        print(f"❌ Error reading model config: {e}")
        return False

def test_dataset_manifest():
    """Test dataset manifest file"""
    print("Testing dataset manifest...")
    
    manifest_path = Path("seed/sample_project/datasets/dataset_manifest.yaml")
    
    try:
        import yaml
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
        
        datasets = manifest.get("datasets", [])
        if len(datasets) < 3:
            print(f"❌ Expected at least 3 datasets, found {len(datasets)}")
            return False
        
        required_fields = ["name", "version", "license", "provider", "type"]
        for dataset in datasets:
            for field in required_fields:
                if field not in dataset:
                    print(f"❌ Dataset missing field '{field}': {dataset.get('name', 'unknown')}")
                    return False
        
        print(f"✅ Dataset manifest valid with {len(datasets)} datasets")
        return True
        
    except ImportError:
        print("⚠ PyYAML not available, skipping dataset manifest test")
        return True
    except Exception as e:
        print(f"❌ Error reading dataset manifest: {e}")
        return False

def test_prompt_files():
    """Test prompt files"""
    print("Testing prompt files...")
    
    prompt_dir = Path("seed/sample_project/prompts")
    prompt_files = ["system_prompt.txt", "classification_prompt.txt", "qa_prompt.txt"]
    
    for prompt_file in prompt_files:
        prompt_path = prompt_dir / prompt_file
        
        if not prompt_path.exists():
            print(f"❌ Missing prompt file: {prompt_file}")
            return False
        
        try:
            with open(prompt_path, 'r') as f:
                content = f.read().strip()
            
            if len(content) < 50:
                print(f"❌ Prompt file too short: {prompt_file}")
                return False
                
        except Exception as e:
            print(f"❌ Error reading prompt file {prompt_file}: {e}")
            return False
    
    print(f"✅ All {len(prompt_files)} prompt files valid")
    return True

def test_python_syntax():
    """Test Python files for syntax errors"""
    print("Testing Python file syntax...")
    
    python_files = [
        "seed/sample_project/train.py",
        "seed/sample_project/data_processing.py", 
        "seed/sample_project/evaluation.py",
        "seed/sample_project/tools/model_utils.py",
        "seed/create_demo_project.py",
        "seed/apply_demo_changes.py"
    ]
    
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                code = f.read()
            
            compile(code, py_file, 'exec')
            
        except SyntaxError as e:
            print(f"❌ Syntax error in {py_file}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error checking {py_file}: {e}")
            return False
    
    print(f"✅ All {len(python_files)} Python files have valid syntax")
    return True

def test_database_scripts():
    """Test database initialization scripts"""
    print("Testing database scripts...")
    
    # Test that scripts can be imported (basic syntax check)
    try:
        # Test create_demo_project.py import
        sys.path.insert(0, "seed")
        
        # Check if files exist and have valid syntax
        script_files = ["create_demo_project.py", "apply_demo_changes.py"]
        
        for script_file in script_files:
            script_path = Path("seed") / script_file
            if not script_path.exists():
                print(f"❌ Script file missing: {script_file}")
                return False
            
            # Test syntax by compiling
            with open(script_path, 'r') as f:
                code = f.read()
            
            try:
                compile(code, str(script_path), 'exec')
            except SyntaxError as e:
                print(f"❌ Syntax error in {script_file}: {e}")
                return False
        
        # Try to import without executing database connections
        try:
            import create_demo_project
            import apply_demo_changes
            
            # Check that main classes exist
            if not hasattr(create_demo_project, 'DemoProjectInitializer'):
                print("❌ DemoProjectInitializer class not found")
                return False
            
            if not hasattr(apply_demo_changes, 'DemoChangeApplicator'):
                print("❌ DemoChangeApplicator class not found")
                return False
                
        except ImportError as e:
            # Expected if database modules aren't available
            if "get_db_connection" in str(e) or "core.db" in str(e):
                print("⚠ Database modules not available (expected in test environment)")
            else:
                print(f"❌ Unexpected import error: {e}")
                return False
        
        print("✅ Database scripts have valid syntax and structure")
        return True
        
    except Exception as e:
        print(f"❌ Error testing database scripts: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=== ML-BOM Autopilot Seed Data Tests ===\n")
    
    tests = [
        test_sample_project_structure,
        test_model_config,
        test_dataset_manifest,
        test_prompt_files,
        test_python_syntax,
        test_database_scripts
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Seed data is ready for use.")
        return True
    else:
        print("💥 Some tests failed. Please fix issues before using seed data.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)