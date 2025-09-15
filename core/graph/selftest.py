#!/usr/bin/env python3
"""
Self-test system for AI-BOM Autopilot
"""

import sys
import os
from typing import Dict, Any
import logging

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from core.db.connection import db_manager
from core.schemas.models import Project

logger = logging.getLogger(__name__)

def selftest() -> Dict[str, Any]:
    """
    Comprehensive self-test of the AI-BOM Autopilot system
    Returns test results and system status
    """
    results = {
        'status': 'unknown',
        'tests': {},
        'capabilities': {},
        'errors': []
    }
    
    try:
        # Test 1: Database connectivity
        results['tests']['database'] = test_database()
        
        # Test 2: Core imports
        results['tests']['imports'] = test_imports()
        
        # Test 3: Environment configuration
        results['tests']['environment'] = test_environment()
        
        # Test 4: Component initialization
        results['tests']['components'] = test_components()
        
        # Collect capabilities
        results['capabilities'] = collect_capabilities()
        
        # Determine overall status
        all_passed = all(test['status'] == 'pass' for test in results['tests'].values())
        results['status'] = 'healthy' if all_passed else 'degraded'
        
    except Exception as e:
        results['status'] = 'error'
        results['errors'].append(str(e))
        logger.error(f"Self-test failed: {e}")
    
    return results

def test_database() -> Dict[str, Any]:
    """Test database connectivity and capabilities"""
    test_result = {
        'status': 'unknown',
        'details': {},
        'errors': []
    }
    
    try:
        # Test basic connection
        health = db_manager.health_check()
        test_result['details']['connection'] = health['status']
        
        if health['status'] == 'healthy':
            test_result['status'] = 'pass'
            test_result['details']['capabilities'] = db_manager.capabilities
        else:
            test_result['status'] = 'fail'
            test_result['errors'].append(health.get('error', 'Unknown database error'))
            
    except Exception as e:
        test_result['status'] = 'fail'
        test_result['errors'].append(str(e))
    
    return test_result

def test_imports() -> Dict[str, Any]:
    """Test critical imports"""
    test_result = {
        'status': 'unknown',
        'details': {},
        'errors': []
    }
    
    critical_imports = [
        ('core.schemas.models', 'Project'),
        ('core.scan_git.scanner', 'GitScanner'),
        ('core.scan_hf.fetcher', 'HuggingFaceFetcher'),
        ('core.normalize.classifier', 'ArtifactClassifier'),
        ('core.embeddings.embedder', 'EmbeddingService'),
        ('core.bom.generator', 'BOMGenerator'),
        ('core.diff.engine', 'DiffEngine'),
        ('core.policy.engine', 'PolicyEngine'),
        ('core.mcp_tools.slack', 'SlackNotifier'),
        ('core.mcp_tools.jira', 'JiraNotifier'),
        ('core.graph.workflow', 'MLBOMWorkflow'),
    ]
    
    passed = 0
    total = len(critical_imports)
    
    for module_name, class_name in critical_imports:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            test_result['details'][f'{module_name}.{class_name}'] = 'ok'
            passed += 1
        except Exception as e:
            test_result['details'][f'{module_name}.{class_name}'] = f'error: {e}'
            test_result['errors'].append(f'{module_name}.{class_name}: {e}')
    
    test_result['status'] = 'pass' if passed == total else 'fail'
    test_result['details']['summary'] = f'{passed}/{total} imports successful'
    
    return test_result

def test_environment() -> Dict[str, Any]:
    """Test environment configuration"""
    test_result = {
        'status': 'unknown',
        'details': {},
        'errors': []
    }
    
    from decouple import config
    
    # Required environment variables
    required_vars = [
        'TIDB_URL',
        'DB_USER', 
        'DB_PASS',
        'OPENAI_API_KEY'
    ]
    
    # Optional environment variables
    optional_vars = [
        'SLACK_WEBHOOK_URL',
        'JIRA_URL',
        'JIRA_USERNAME',
        'JIRA_API_TOKEN'
    ]
    
    missing_required = []
    
    for var in required_vars:
        value = config(var, default=None)
        if value:
            test_result['details'][var] = 'configured'
        else:
            test_result['details'][var] = 'missing'
            missing_required.append(var)
    
    for var in optional_vars:
        value = config(var, default=None)
        test_result['details'][var] = 'configured' if value else 'not configured'
    
    if missing_required:
        test_result['status'] = 'fail'
        test_result['errors'].append(f'Missing required variables: {", ".join(missing_required)}')
    else:
        test_result['status'] = 'pass'
    
    return test_result

def test_components() -> Dict[str, Any]:
    """Test component initialization"""
    test_result = {
        'status': 'unknown',
        'details': {},
        'errors': []
    }
    
    components_to_test = [
        ('GitScanner', 'core.scan_git.scanner', 'GitScanner'),
        ('HuggingFaceFetcher', 'core.scan_hf.fetcher', 'HuggingFaceFetcher'),
        ('ArtifactClassifier', 'core.normalize.classifier', 'ArtifactClassifier'),
        ('EmbeddingService', 'core.embeddings.embedder', 'EmbeddingService'),
        ('BOMGenerator', 'core.bom.generator', 'BOMGenerator'),
        ('DiffEngine', 'core.diff.engine', 'DiffEngine'),
        ('PolicyEngine', 'core.policy.engine', 'PolicyEngine'),
        ('SlackNotifier', 'core.mcp_tools.slack', 'SlackNotifier'),
        ('JiraNotifier', 'core.mcp_tools.jira', 'JiraNotifier'),
    ]
    
    passed = 0
    total = len(components_to_test)
    
    for component_name, module_name, class_name in components_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            component_class = getattr(module, class_name)
            instance = component_class()
            test_result['details'][component_name] = 'initialized'
            passed += 1
        except Exception as e:
            test_result['details'][component_name] = f'error: {e}'
            test_result['errors'].append(f'{component_name}: {e}')
    
    test_result['status'] = 'pass' if passed == total else 'fail'
    test_result['details']['summary'] = f'{passed}/{total} components initialized'
    
    return test_result

def collect_capabilities() -> Dict[str, Any]:
    """Collect system capabilities"""
    capabilities = {
        'database': db_manager.capabilities,
        'python_version': sys.version,
        'platform': sys.platform,
    }
    
    # Test vector search capability
    if db_manager.capabilities.get('vector'):
        capabilities['vector_search'] = 'available'
    else:
        capabilities['vector_search'] = 'unavailable (will use fallback)'
    
    # Test full-text search capability
    if db_manager.capabilities.get('fulltext'):
        capabilities['fulltext_search'] = 'available'
    else:
        capabilities['fulltext_search'] = 'unavailable (will use BM25 fallback)'
    
    # Test OpenAI client
    try:
        from core.embeddings.embedder import EmbeddingService
        embedder = EmbeddingService()
        capabilities['embeddings'] = 'available' if embedder.client else 'unavailable'
    except Exception:
        capabilities['embeddings'] = 'unavailable'
    
    return capabilities

def print_selftest_results(results: Dict[str, Any]):
    """Print formatted self-test results"""
    print("🔍 AI-BOM Autopilot Self-Test Results")
    print("=" * 50)
    
    # Overall status
    status_icon = "✅" if results['status'] == 'healthy' else "⚠️" if results['status'] == 'degraded' else "❌"
    print(f"\nOverall Status: {status_icon} {results['status'].upper()}")
    
    # Test results
    print("\n📋 Test Results:")
    for test_name, test_result in results['tests'].items():
        status_icon = "✅" if test_result['status'] == 'pass' else "❌"
        print(f"  {status_icon} {test_name.title()}: {test_result['status']}")
        
        if test_result.get('errors'):
            for error in test_result['errors']:
                print(f"    ⚠️  {error}")
    
    # Capabilities
    print("\n🔧 System Capabilities:")
    capabilities = results['capabilities']
    
    print(f"  • Database: {capabilities['database']['version'] or 'Unknown version'}")
    print(f"  • Vector Search: {capabilities.get('vector_search', 'unknown')}")
    print(f"  • Full-text Search: {capabilities.get('fulltext_search', 'unknown')}")
    print(f"  • Embeddings: {capabilities.get('embeddings', 'unknown')}")
    print(f"  • Python: {capabilities['python_version'].split()[0]}")
    
    # Errors
    if results.get('errors'):
        print("\n❌ System Errors:")
        for error in results['errors']:
            print(f"  • {error}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    # Run self-test
    results = selftest()
    print_selftest_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if results['status'] in ['healthy', 'degraded'] else 1)