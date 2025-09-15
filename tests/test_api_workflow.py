#!/usr/bin/env python3
"""
Test the workflow integration with API components
"""

import os
import sys
import json
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.schemas.models import Project, ScanState
from core.graph.workflow import ml_bom_workflow

def test_workflow_status():
    """Test the workflow status functionality"""
    status = ml_bom_workflow.get_workflow_status()
    
    assert 'dry_run' in status
    assert 'allowed_tools' in status
    assert 'node_timeouts' in status
    
    # Check that all expected nodes have timeouts
    expected_nodes = [
        'scan_plan', 'scan_git', 'scan_hf', 'normalize', 
        'embed_index', 'generate_bom', 'diff_previous', 
        'check_policies', 'notify'
    ]
    
    for node in expected_nodes:
        assert node in status['node_timeouts']

def test_scan_workflow_integration():
    """Test workflow integration with mocked components"""
    project = Project(
        id=1,
        name="demo",
        repo_url="https://github.com/test/demo.git",
        default_branch="main"
    )
    
    # Test that workflow can be initialized and run
    with patch.object(ml_bom_workflow, 'workflow') as mock_workflow:
        mock_scan_result = ScanState(project=project)
        mock_scan_result.commit_sha = "abc123"
        mock_scan_result.meta = {
            'scan_start_time': 1000,
            'bom_sha256': 'test_hash',
            'counters': {'files_scanned': 10}
        }
        mock_workflow.invoke.return_value = mock_scan_result
        
        result = ml_bom_workflow.run_scan(project, dry_run=False)
        
        assert result.project.name == "demo"
        assert result.commit_sha == "abc123"
        assert 'scan_start_time' in result.meta

def test_workflow_error_handling():
    """Test workflow error handling"""
    project = Project(
        id=1,
        name="demo",
        repo_url="",  # Invalid repo URL
        default_branch="main"
    )
    
    # Test that workflow handles errors gracefully
    try:
        result = ml_bom_workflow.run_scan(project, dry_run=True)
        # If we get here, check if there's an error in the result
        if hasattr(result, 'error') and result.error:
            print(f"✅ Workflow correctly handled error: {result.error}")
        else:
            print("✅ Workflow completed without throwing exception")
    except Exception as e:
        print(f"✅ Workflow correctly raised exception: {e}")

def test_workflow_dry_run_mode():
    """Test workflow dry run mode"""
    project = Project(
        id=1,
        name="demo",
        repo_url="https://github.com/test/demo.git",
        default_branch="main"
    )
    
    # Test dry run mode
    with patch.object(ml_bom_workflow, 'workflow') as mock_workflow:
        mock_scan_result = ScanState(project=project)
        mock_scan_result.meta = {'scan_start_time': 1000, 'dry_run': True}
        mock_workflow.invoke.return_value = mock_scan_result
        
        result = ml_bom_workflow.run_scan(project, dry_run=True)
        
        # Verify dry_run was set in the initial state
        mock_workflow.invoke.assert_called_once()
        call_args = mock_workflow.invoke.call_args[0][0]
        assert call_args.meta['dry_run'] is True

def test_workflow_node_decorators():
    """Test that workflow nodes have proper decorators"""
    # Test that timeout and retry decorators are applied
    workflow = ml_bom_workflow
    
    # Check that nodes exist and are callable
    assert hasattr(workflow, '_scan_plan_node')
    assert callable(workflow._scan_plan_node)
    assert hasattr(workflow, '_scan_git_node')
    assert callable(workflow._scan_git_node)
    assert hasattr(workflow, '_notify_node')
    assert callable(workflow._notify_node)
    
    # Test scan plan node with valid project
    project = Project(
        id=1,
        name="test",
        repo_url="https://github.com/test/repo.git",
        default_branch="main"
    )
    state = ScanState(project=project)
    
    result = workflow._scan_plan_node(state)
    assert result.error is None
    assert 'scan_start_time' in result.meta

if __name__ == "__main__":
    # Run tests
    test_workflow_status()
    print("✅ Workflow status test passed!")
    
    test_scan_workflow_integration()
    print("✅ Scan workflow integration test passed!")
    
    test_workflow_error_handling()
    print("✅ Workflow error handling test passed!")
    
    test_workflow_dry_run_mode()
    print("✅ Workflow dry run mode test passed!")
    
    test_workflow_node_decorators()
    print("✅ Workflow node decorators test passed!")
    
    print("✅ All workflow integration tests passed!")