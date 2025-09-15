#!/usr/bin/env python3
"""
Test API endpoints with mock data
"""

import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

def test_api_endpoints():
    """Test API endpoints with mock database"""
    print("🔍 Testing API endpoints...")
    
    try:
        from apps.api.main import app
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert "status" in health_data
        print("  ✅ /health endpoint working")
        
        # Mock database for other endpoints
        with patch('apps.api.main.db_manager') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            
            # Mock projects list
            mock_session.execute.return_value = []
            
            response = client.get("/projects")
            assert response.status_code == 200
            print("  ✅ /projects endpoint working")
            
            # Test project creation
            project_data = {
                "name": "test-project",
                "repo_url": "https://github.com/test/repo",
                "default_branch": "main"
            }
            
            mock_session.execute.return_value.lastrowid = 1
            
            response = client.post("/projects", json=project_data)
            assert response.status_code == 200
            print("  ✅ POST /projects endpoint working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API test failed: {e}")
        return False

def test_streamlit_import():
    """Test Streamlit UI imports"""
    print("🔍 Testing Streamlit UI...")
    
    try:
        # Test that the Streamlit app can be imported
        with patch('streamlit.set_page_config'):
            with patch('streamlit.title'):
                with patch('streamlit.sidebar'):
                    import apps.ui.streamlit_app
        
        print("  ✅ Streamlit app imports successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Streamlit test failed: {e}")
        return False

def main():
    """Run API tests"""
    print("🚀 Testing AI-BOM Autopilot API & UI...\n")
    
    tests = [
        ("API Endpoints", test_api_endpoints),
        ("Streamlit UI", test_streamlit_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        if test_func():
            passed += 1
            print(f"✅ {test_name} passed!")
        else:
            print(f"❌ {test_name} failed!")
    
    print(f"\n🎯 API Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API tests passed! Ready for deployment.")
        return True
    else:
        print("❌ Some API tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)