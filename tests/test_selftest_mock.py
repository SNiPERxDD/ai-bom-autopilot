#!/usr/bin/env python3
"""
Test the selftest function with mocked database connection
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_selftest_mock():
    """Test selftest function with mocked dependencies"""
    print("🧪 Testing Self-Test Function (Mocked)")
    print("=" * 45)
    
    try:
        # Mock the database manager and config
        with patch('core.db.migrations.db_manager') as mock_db_manager, \
             patch('core.db.migrations.config') as mock_config:
            
            # Setup mock database manager
            mock_db_manager.health_check.return_value = {
                "status": "healthy",
                "capabilities": {
                    "version": "TiDB 7.1.0",
                    "vector": True,
                    "fulltext": True
                }
            }
            
            # Setup mock engine and connection
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0.0  # Perfect cosine distance
            mock_conn.execute.return_value = mock_result
            mock_db_manager.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Setup mock config values
            mock_config.side_effect = lambda key, default='': {
                'EMBED_PROVIDER': 'openai',
                'OPENAI_API_KEY': 'sk-test-key-123',
                'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/services/test',
                'JIRA_URL': 'https://test.atlassian.net',
                'JIRA_API_TOKEN': 'test-token',
                'HF_TOKEN': 'hf_test_token'
            }.get(key, default)
            
            # Set FTS_ENABLED to True for this test
            import core.db.migrations
            original_fts = core.db.migrations.FTS_ENABLED
            core.db.migrations.FTS_ENABLED = True
            
            try:
                # Import and run selftest
                from core.db.migrations import selftest
                
                print("Running selftest with mocked dependencies...")
                result = selftest()
                
                if result:
                    print("✅ Selftest completed successfully with mocked data")
                else:
                    print("❌ Selftest failed")
                    return False
                    
            finally:
                # Restore original FTS_ENABLED value
                core.db.migrations.FTS_ENABLED = original_fts
        
        return True
        
    except Exception as e:
        print(f"❌ Mock selftest failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_selftest_mock()
    if not success:
        sys.exit(1)
    
    print("\n🎉 Mock selftest passed! The selftest function is working correctly.")