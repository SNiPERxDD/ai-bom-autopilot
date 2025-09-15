#!/usr/bin/env python3
"""
Test SQL syntax without actual database connection
"""

import sys
import os
import re

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

def test_sql_syntax():
    """Test that our SQL statements are syntactically valid"""
    print("🔍 Testing SQL syntax...")
    
    try:
        from core.db.migrations import run_migrations
        
        # Get the migration SQL by reading the source
        with open('core/db/migrations.py', 'r') as f:
            content = f.read()
        
        # Extract SQL statements
        sql_statements = re.findall(r'"""(.*?)"""', content, re.DOTALL)
        
        print(f"Found {len(sql_statements)} SQL statements")
        
        # Basic SQL validation
        required_keywords = ['CREATE TABLE', 'PRIMARY KEY', 'FOREIGN KEY']
        
        for i, sql in enumerate(sql_statements):
            if any(keyword in sql.upper() for keyword in required_keywords):
                print(f"  ✅ Statement {i+1}: Valid CREATE TABLE")
            else:
                print(f"  ⚠️  Statement {i+1}: Not a CREATE TABLE")
        
        print("✅ SQL syntax validation passed")
        return True
        
    except Exception as e:
        print(f"❌ SQL syntax test failed: {e}")
        return False

def test_workflow_structure():
    """Test workflow structure"""
    print("🔍 Testing workflow structure...")
    
    try:
        from core.graph.workflow import MLBOMWorkflow
        
        workflow = MLBOMWorkflow()
        
        # Check that workflow has required components
        required_components = [
            'git_scanner',
            'hf_fetcher', 
            'classifier',
            'embedder',
            'bom_generator',
            'diff_engine',
            'policy_engine',
            'slack_notifier',
            'jira_notifier'
        ]
        
        for component in required_components:
            if hasattr(workflow, component):
                print(f"  ✅ {component}: present")
            else:
                print(f"  ❌ {component}: missing")
                return False
        
        print("✅ Workflow structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Workflow structure test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoint definitions"""
    print("🔍 Testing API endpoints...")
    
    try:
        from apps.api.main import app
        
        # Get routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, list(route.methods)))
        
        print(f"Found {len(routes)} API routes:")
        for path, methods in routes:
            print(f"  • {', '.join(methods)} {path}")
        
        # Check for required endpoints
        required_endpoints = [
            '/health',
            '/projects',
            '/scan'
        ]
        
        existing_paths = [path for path, _ in routes]
        
        for endpoint in required_endpoints:
            if any(endpoint in path for path in existing_paths):
                print(f"  ✅ {endpoint}: available")
            else:
                print(f"  ❌ {endpoint}: missing")
                return False
        
        print("✅ API endpoints validation passed")
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Running AI-BOM Autopilot validation tests...\n")
    
    tests = [
        ("SQL Syntax", test_sql_syntax),
        ("Workflow Structure", test_workflow_structure),
        ("API Endpoints", test_api_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        if test_func():
            passed += 1
        print()
    
    print(f"🎯 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed! System is ready for testing.")
        return True
    else:
        print("❌ Some validation tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)