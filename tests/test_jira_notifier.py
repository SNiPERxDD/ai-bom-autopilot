#!/usr/bin/env python3
"""
Test script for JiraNotifier functionality
"""

import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.mcp_tools.jira import JiraNotifier
from core.schemas.models import (
    ScanState, Project, PolicyEvent, Severity, 
    Action, ActionKind, ActionStatus,
    Model, Dataset, Prompt, Tool, ToolType
)

def test_jira_ticket_construction():
    """Test that Jira ticket payloads are properly constructed"""
    print("Testing Jira ticket construction...")
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    high_events = [
        PolicyEvent(
            id=1,
            project_id=1,
            severity=Severity.HIGH,
            rule="missing_license",
            artifact={"name": "dangerous-model", "type": "model"},
            details={"message": "Critical security vulnerability detected"},
            dedupe_key="missing_license:dangerous-model"
        ),
        PolicyEvent(
            id=2,
            project_id=1,
            severity=Severity.HIGH,
            rule="unapproved_license",
            artifact={"name": "restricted-dataset", "type": "dataset"},
            details={"message": "Dataset uses GPL license which is not approved"},
            dedupe_key="unapproved_license:restricted-dataset"
        )
    ]
    
    state = ScanState(
        project=project,
        commit_sha="abc123def456",
        models=[Model(id=1, project_id=1, name="test-model", provider="huggingface", version="1.0")],
        datasets=[Dataset(id=1, project_id=1, name="test-dataset", version="1.0")],
        policy_events=high_events
    )
    
    # Create JiraNotifier
    notifier = JiraNotifier()
    
    # Test ticket construction
    ticket_data = notifier._build_ticket_data(state, high_events)
    
    # Verify structure
    assert "fields" in ticket_data
    fields = ticket_data["fields"]
    
    # Check required fields
    assert "project" in fields
    assert "summary" in fields
    assert "description" in fields
    assert "issuetype" in fields
    assert "priority" in fields
    assert "labels" in fields
    
    # Check content
    assert "test-project" in fields["summary"]
    assert fields["priority"]["name"] == "High"
    assert fields["issuetype"]["name"] == "Bug"
    assert "ml-bom" in fields["labels"]
    assert "policy-violation" in fields["labels"]
    
    # Check description contains policy details
    description_text = fields["description"]["content"][0]["content"][0]["text"]
    assert "missing_license" in description_text
    assert "unapproved_license" in description_text
    assert "dangerous-model" in description_text
    assert "restricted-dataset" in description_text
    
    print("✅ Jira ticket construction test passed")

def test_summary_ticket_construction():
    """Test summary ticket construction"""
    print("Testing summary ticket construction...")
    
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(
        project=project,
        commit_sha="abc123def456",
        models=[Model(id=1, project_id=1, name="test-model", provider="huggingface", version="1.0")],
        datasets=[Dataset(id=1, project_id=1, name="test-dataset", version="1.0")],
        policy_events=[
            PolicyEvent(
                id=1,
                project_id=1,
                severity=Severity.MEDIUM,
                rule="minor_issue",
                artifact={"name": "test-model", "type": "model"},
                details={"message": "Minor configuration issue"},
                dedupe_key="minor_issue:test-model"
            )
        ]
    )
    
    notifier = JiraNotifier()
    ticket_data = notifier._build_summary_ticket_data(state)
    
    # Verify structure
    fields = ticket_data["fields"]
    assert fields["issuetype"]["name"] == "Task"
    assert fields["priority"]["name"] == "Medium"  # Should be Medium due to policy events
    assert "scan-summary" in fields["labels"]
    
    # Check description contains scan details
    description_text = fields["description"]["content"][0]["content"][0]["text"]
    assert "Models: 1" in description_text
    assert "Datasets: 1" in description_text
    assert "Policy Events: 1" in description_text
    
    print("✅ Summary ticket construction test passed")

@patch('core.mcp_tools.jira.requests.post')
def test_jira_api_call(mock_post):
    """Test Jira API call functionality"""
    print("Testing Jira API call...")
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"key": "MLBOM-123", "id": "10001"}
    mock_response.text = '{"key": "MLBOM-123"}'
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    high_events = [
        PolicyEvent(
            id=1,
            project_id=1,
            severity=Severity.HIGH,
            rule="missing_license",
            artifact={"name": "dangerous-model", "type": "model"},
            details={"message": "Critical issue"},
            dedupe_key="missing_license:dangerous-model"
        )
    ]
    state = ScanState(project=project, policy_events=high_events)
    
    # Create notifier with mock config
    with patch('core.mcp_tools.jira.config') as mock_config:
        def config_side_effect(key, default=None):
            config_map = {
                'JIRA_URL': 'https://test.atlassian.net',
                'JIRA_USERNAME': 'test@example.com',
                'JIRA_API_TOKEN': 'test-token',
                'JIRA_PROJECT_KEY': 'MLBOM'
            }
            return config_map.get(key, default)
        
        mock_config.side_effect = config_side_effect
        notifier = JiraNotifier()
        
        # Create ticket
        action = notifier.create_policy_ticket(state)
        
        # Verify API call was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL and headers
        assert call_args[0][0] == "https://test.atlassian.net/rest/api/3/issue"
        assert "Authorization" in call_args[1]["headers"]
        assert "Basic" in call_args[1]["headers"]["Authorization"]
        assert call_args[1]["timeout"] == 30
        
        # Check action record
        assert action is not None
        assert action.kind == ActionKind.JIRA
        assert action.status == ActionStatus.OK
        assert action.project_id == 1
        assert action.response["ticket_key"] == "MLBOM-123"
        assert "ticket_url" in action.response
    
    print("✅ Jira API call test passed")

@patch('core.mcp_tools.jira.requests.post')
def test_jira_error_handling(mock_post):
    """Test error handling for failed Jira API calls"""
    print("Testing Jira error handling...")
    
    # Mock failed response
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request - Invalid project key"
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    high_events = [
        PolicyEvent(
            id=1,
            project_id=1,
            severity=Severity.HIGH,
            rule="missing_license",
            artifact={"name": "dangerous-model", "type": "model"},
            details={"message": "Critical issue"},
            dedupe_key="missing_license:dangerous-model"
        )
    ]
    state = ScanState(project=project, policy_events=high_events)
    
    # Create notifier with mock config
    with patch('core.mcp_tools.jira.config') as mock_config:
        def config_side_effect(key, default=None):
            config_map = {
                'JIRA_URL': 'https://test.atlassian.net',
                'JIRA_USERNAME': 'test@example.com',
                'JIRA_API_TOKEN': 'test-token',
                'JIRA_PROJECT_KEY': 'MLBOM'
            }
            return config_map.get(key, default)
        
        mock_config.side_effect = config_side_effect
        notifier = JiraNotifier()
        
        # Create ticket
        action = notifier.create_policy_ticket(state)
        
        # Check action record shows failure
        assert action is not None
        assert action.status == ActionStatus.FAIL
        assert action.response['status_code'] == 400
    
    print("✅ Jira error handling test passed")

def test_jira_not_configured():
    """Test behavior when Jira is not configured"""
    print("Testing Jira not configured...")
    
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    high_events = [
        PolicyEvent(
            id=1,
            project_id=1,
            severity=Severity.HIGH,
            rule="missing_license",
            artifact={"name": "dangerous-model", "type": "model"},
            details={"message": "Critical issue"},
            dedupe_key="missing_license:dangerous-model"
        )
    ]
    state = ScanState(project=project, policy_events=high_events)
    
    # Create notifier without config
    with patch('core.mcp_tools.jira.config') as mock_config:
        mock_config.return_value = None
        notifier = JiraNotifier()
        
        # Try to create ticket
        action = notifier.create_policy_ticket(state)
        
        # Should return None when not configured
        assert action is None
    
    print("✅ Jira not configured test passed")

def test_no_high_severity_events():
    """Test that tickets are only created for high-severity events"""
    print("Testing no high-severity events...")
    
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    low_events = [
        PolicyEvent(
            id=1,
            project_id=1,
            severity=Severity.LOW,
            rule="minor_issue",
            artifact={"name": "test-model", "type": "model"},
            details={"message": "Minor issue"},
            dedupe_key="minor_issue:test-model"
        )
    ]
    state = ScanState(project=project, policy_events=low_events)
    
    # Create configured notifier
    with patch('core.mcp_tools.jira.config') as mock_config:
        def config_side_effect(key, default=None):
            config_map = {
                'JIRA_URL': 'https://test.atlassian.net',
                'JIRA_USERNAME': 'test@example.com',
                'JIRA_API_TOKEN': 'test-token',
                'JIRA_PROJECT_KEY': 'MLBOM'
            }
            return config_map.get(key, default)
        
        mock_config.side_effect = config_side_effect
        notifier = JiraNotifier()
        
        # Try to create ticket
        action = notifier.create_policy_ticket(state)
        
        # Should return None for low-severity events
        assert action is None
    
    print("✅ No high-severity events test passed")

def run_all_tests():
    """Run all JiraNotifier tests"""
    print("🧪 Running JiraNotifier tests...\n")
    
    try:
        test_jira_ticket_construction()
        test_summary_ticket_construction()
        test_jira_api_call()
        test_jira_error_handling()
        test_jira_not_configured()
        test_no_high_severity_events()
        
        print("\n✅ All JiraNotifier tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)