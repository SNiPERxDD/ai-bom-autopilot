#!/usr/bin/env python3
"""
Integration test for the LangGraph workflow
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.schemas.models import Project, ScanState
from core.graph.workflow import MLBOMWorkflow

def test_workflow_initialization():
    """Test that the workflow initializes correctly"""
    workflow = MLBOMWorkflow()
    
    # Check that all services are initialized
    assert workflow.git_scanner is not None
    assert workflow.hf_fetcher is not None
    assert workflow.classifier is not None
    assert workflow.embedder is not None
    assert workflow.bom_generator is not None
    assert workflow.diff_engine is not None
    assert workflow.policy_engine is not None
    assert workflow.slack_notifier is not None
    assert workflow.jira_notifier is not None
    
    # Check workflow configuration
    assert workflow.workflow is not None
    assert isinstance(workflow.allowed_tools, set)
    assert 'slack' in workflow.allowed_tools
    assert 'jira' in workflow.allowed_tools

def test_workflow_status():
    """Test workflow status reporting"""
    workflow = MLBOMWorkflow()
    status = workflow.get_workflow_status()
    
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
        assert isinstance(status['node_timeouts'][node], int)
        assert status['node_timeouts'][node] > 0

def test_scan_plan_node():
    """Test the scan plan node"""
    workflow = MLBOMWorkflow()
    
    # Create test project
    project = Project(
        id=1,
        name="test-project",
        repo_url="https://github.com/test/repo.git",
        default_branch="main"
    )
    
    # Create initial state
    state = ScanState(project=project)
    
    # Run scan plan node
    result = workflow._scan_plan_node(state)
    
    # Check that planning was successful
    assert result.error is None
    assert 'scan_start_time' in result.meta
    assert 'workflow_version' in result.meta
    assert 'counters' in result.meta
    assert result.meta['workflow_version'] == '1.0'

def test_scan_plan_node_missing_repo():
    """Test scan plan node with missing repo URL"""
    workflow = MLBOMWorkflow()
    
    # Create test project without repo URL
    project = Project(
        id=1,
        name="test-project",
        repo_url="",  # Missing repo URL
        default_branch="main"
    )
    
    # Create initial state
    state = ScanState(project=project)
    
    # Run scan plan node
    result = workflow._scan_plan_node(state)
    
    # Check that planning failed appropriately
    assert result.error is not None
    assert "repo_url is required" in result.error

@patch('core.graph.workflow.db_manager')
def test_should_skip_diff(mock_db_manager):
    """Test diff skipping logic"""
    workflow = MLBOMWorkflow()
    
    # Mock database session
    mock_session = Mock()
    mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
    
    # Test case: First BOM (count = 0)
    mock_result = Mock()
    mock_result.count = 0
    mock_session.execute.return_value.fetchone.return_value = mock_result
    
    project = Project(id=1, name="test", repo_url="https://test.git")
    state = ScanState(project=project)
    
    should_skip = workflow.should_skip_diff(state)
    assert should_skip is True
    
    # Test case: Second BOM (count = 1)
    mock_result.count = 1
    should_skip = workflow.should_skip_diff(state)
    assert should_skip is True
    
    # Test case: Third BOM (count = 2)
    mock_result.count = 2
    should_skip = workflow.should_skip_diff(state)
    assert should_skip is False

def test_should_skip_notifications():
    """Test notification skipping logic"""
    workflow = MLBOMWorkflow()
    
    project = Project(id=1, name="test", repo_url="https://test.git")
    
    # Test case: Dry run mode
    state = ScanState(project=project)
    state.meta['dry_run'] = True
    
    should_skip = workflow.should_skip_notifications(state)
    assert should_skip is True
    
    # Test case: No policy events
    state.meta['dry_run'] = False
    state.policy_events = []
    
    should_skip = workflow.should_skip_notifications(state)
    assert should_skip is True
    
    # Test case: Has policy events, not dry run
    from core.schemas.models import PolicyEvent, Severity
    state.policy_events = [
        PolicyEvent(
            project_id=1,
            severity=Severity.HIGH,
            rule="test_rule",
            artifact={},
            details={},
            dedupe_key="test"
        )
    ]
    
    should_skip = workflow.should_skip_notifications(state)
    assert should_skip is False

def test_dry_run_workflow():
    """Test that dry run mode is properly handled"""
    workflow = MLBOMWorkflow()
    
    project = Project(
        id=1,
        name="test-project",
        repo_url="https://github.com/test/repo.git",
        default_branch="main"
    )
    
    # Test dry run initialization
    with patch.object(workflow, 'workflow') as mock_workflow:
        mock_workflow.invoke.return_value = ScanState(project=project)
        
        result = workflow.run_scan(project, dry_run=True)
        
        # Check that dry_run was set in state
        mock_workflow.invoke.assert_called_once()
        call_args = mock_workflow.invoke.call_args[0][0]
        assert call_args.meta['dry_run'] is True

if __name__ == "__main__":
    # Run basic tests
    test_workflow_initialization()
    test_workflow_status()
    test_scan_plan_node()
    test_scan_plan_node_missing_repo()
    test_should_skip_notifications()
    test_dry_run_workflow()
    
    print("✅ All workflow tests passed!")