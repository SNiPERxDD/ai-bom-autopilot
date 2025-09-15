#!/usr/bin/env python3
"""
Test Vector Column Migration

Tests the vector column resize migration functionality with various scenarios.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db.resize_vector_migration import (
    get_current_vector_dimension,
    check_table_exists,
    check_vector_support,
    resize_vector_column,
    validate_migration,
    auto_resize_for_provider
)

class TestVectorMigration(unittest.TestCase):
    """Test vector column migration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Mock database manager
        self.mock_db_manager = MagicMock()
        self.mock_connection = MagicMock()
        self.mock_db_manager.engine.connect.return_value.__enter__.return_value = self.mock_connection
    
    @patch('core.db.resize_vector_migration.db_manager')
    def test_get_current_vector_dimension(self, mock_db_manager):
        """Test getting current vector dimension"""
        mock_db_manager.engine.connect.return_value.__enter__.return_value = self.mock_connection
        
        # Test successful dimension detection
        self.mock_connection.execute.return_value.scalar.return_value = 'VECTOR(1536)'
        result = get_current_vector_dimension()
        self.assertEqual(result, 1536)
        
        # Test different dimension
        self.mock_connection.execute.return_value.scalar.return_value = 'VECTOR(768)'
        result = get_current_vector_dimension()
        self.assertEqual(result, 768)
        
        # Test no vector column
        self.mock_connection.execute.return_value.scalar.return_value = None
        result = get_current_vector_dimension()
        self.assertIsNone(result)
    
    @patch('core.db.resize_vector_migration.db_manager')
    def test_check_table_exists(self, mock_db_manager):
        """Test table existence check"""
        mock_db_manager.engine.connect.return_value.__enter__.return_value = self.mock_connection
        
        # Test table exists
        self.mock_connection.execute.return_value.scalar.return_value = 1
        result = check_table_exists()
        self.assertTrue(result)
        
        # Test table doesn't exist
        self.mock_connection.execute.return_value.scalar.return_value = 0
        result = check_table_exists()
        self.assertFalse(result)
    
    @patch('core.db.resize_vector_migration.db_manager')
    def test_check_vector_support(self, mock_db_manager):
        """Test vector function support check"""
        mock_db_manager.engine.connect.return_value.__enter__.return_value = self.mock_connection
        
        # Test vector support available
        self.mock_connection.execute.return_value = None  # No exception
        result = check_vector_support()
        self.assertTrue(result)
        
        # Test vector support not available
        self.mock_connection.execute.side_effect = Exception("Vector functions not supported")
        result = check_vector_support()
        self.assertFalse(result)
    
    @patch('core.db.resize_vector_migration.get_row_count')
    @patch('core.db.resize_vector_migration.backup_vector_data')
    @patch('core.db.resize_vector_migration.get_current_vector_dimension')
    @patch('core.db.resize_vector_migration.check_vector_support')
    @patch('core.db.resize_vector_migration.check_table_exists')
    @patch('core.db.resize_vector_migration.db_manager')
    def test_resize_vector_column_success(self, mock_db_manager, mock_table_exists, 
                                        mock_vector_support, mock_current_dim, 
                                        mock_backup, mock_row_count):
        """Test successful vector column resize"""
        # Setup mocks
        mock_table_exists.return_value = True
        mock_vector_support.return_value = True
        mock_current_dim.return_value = 1536
        mock_row_count.return_value = 100
        mock_backup.return_value = 'backup_table_123'
        
        mock_connection = MagicMock()
        mock_trans = MagicMock()
        mock_connection.begin.return_value = mock_trans
        mock_db_manager.engine.connect.return_value.__enter__.return_value = mock_connection
        
        # Test resize from 1536 to 768
        result = resize_vector_column(768)
        self.assertTrue(result)
        
        # Verify backup was created
        mock_backup.assert_called_once()
        
        # Verify ALTER TABLE was called
        mock_connection.execute.assert_any_call(unittest.mock.ANY)  # ALTER TABLE call
        
        # Verify transaction was committed
        mock_trans.commit.assert_called_once()
    
    @patch('core.db.resize_vector_migration.get_current_vector_dimension')
    @patch('core.db.resize_vector_migration.check_vector_support')
    @patch('core.db.resize_vector_migration.check_table_exists')
    def test_resize_vector_column_no_change_needed(self, mock_table_exists, 
                                                  mock_vector_support, mock_current_dim):
        """Test resize when no change is needed"""
        mock_table_exists.return_value = True
        mock_vector_support.return_value = True
        mock_current_dim.return_value = 1536
        
        # Test resize to same dimension
        result = resize_vector_column(1536)
        self.assertTrue(result)
    
    @patch('core.db.resize_vector_migration.check_table_exists')
    def test_resize_vector_column_table_not_exists(self, mock_table_exists):
        """Test resize when table doesn't exist"""
        mock_table_exists.return_value = False
        
        result = resize_vector_column(768)
        self.assertFalse(result)
    
    @patch('core.db.resize_vector_migration.check_vector_support')
    @patch('core.db.resize_vector_migration.check_table_exists')
    def test_resize_vector_column_no_vector_support(self, mock_table_exists, mock_vector_support):
        """Test resize when vector functions not supported"""
        mock_table_exists.return_value = True
        mock_vector_support.return_value = False
        
        result = resize_vector_column(768)
        self.assertFalse(result)
    
    @patch('core.db.resize_vector_migration.get_current_vector_dimension')
    def test_validate_migration(self, mock_current_dim):
        """Test migration validation"""
        # Test successful validation
        mock_current_dim.return_value = 768
        result = validate_migration(768)
        self.assertTrue(result)
        
        # Test failed validation
        mock_current_dim.return_value = 1536
        result = validate_migration(768)
        self.assertFalse(result)
    
    @patch('core.db.resize_vector_migration.validate_migration')
    @patch('core.db.resize_vector_migration.resize_vector_column')
    def test_auto_resize_for_provider_openai(self, mock_resize, mock_validate):
        """Test auto-resize for OpenAI provider"""
        mock_resize.return_value = True
        mock_validate.return_value = True
        
        with patch.dict(os.environ, {
            'EMBED_PROVIDER': 'openai',
            'EMBEDDING_DIM': '1536'
        }):
            result = auto_resize_for_provider()
            self.assertTrue(result)
            mock_resize.assert_called_once_with(1536)
            mock_validate.assert_called_once_with(1536)
    
    @patch('core.db.resize_vector_migration.validate_migration')
    @patch('core.db.resize_vector_migration.resize_vector_column')
    def test_auto_resize_for_provider_gemini(self, mock_resize, mock_validate):
        """Test auto-resize for Gemini provider"""
        mock_resize.return_value = True
        mock_validate.return_value = True
        
        with patch.dict(os.environ, {
            'EMBED_PROVIDER': 'gemini',
            'EMBEDDING_DIM': '768'
        }):
            result = auto_resize_for_provider()
            self.assertTrue(result)
            mock_resize.assert_called_once_with(768)
            mock_validate.assert_called_once_with(768)
    
    def test_auto_resize_for_provider_missing_dim(self):
        """Test auto-resize with missing EMBEDDING_DIM"""
        with patch.dict(os.environ, {
            'EMBED_PROVIDER': 'openai'
        }, clear=True):
            result = auto_resize_for_provider()
            self.assertFalse(result)

class TestVectorMigrationIntegration(unittest.TestCase):
    """Integration tests for vector migration (requires actual database)"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Skip if no database connection available
        try:
            from core.db.connection import db_manager
            health = db_manager.health_check()
            if health["status"] != "healthy":
                self.skipTest("Database not available for integration tests")
        except Exception:
            self.skipTest("Database connection not configured")
    
    def test_migration_status_check(self):
        """Test getting migration status from real database"""
        # This test requires a real database connection
        # It should be run manually or in CI with proper database setup
        pass

def run_tests():
    """Run all tests"""
    print("🧪 Running Vector Migration Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestVectorMigration))
    
    # Only add integration tests if database is available
    try:
        from core.db.connection import db_manager
        health = db_manager.health_check()
        if health["status"] == "healthy":
            suite.addTests(loader.loadTestsFromTestCase(TestVectorMigrationIntegration))
            print("📊 Including integration tests (database available)")
        else:
            print("⚠️  Skipping integration tests (database not available)")
    except Exception:
        print("⚠️  Skipping integration tests (database not configured)")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)