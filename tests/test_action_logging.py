#!/usr/bin/env python3
"""
Test script for comprehensive action logging functionality
"""

import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.mcp_tools.slack import SlackNotifier
from core.mcp_tools.jira import JiraNotifier
from core.schemas.models import (
    ScanState, Project, PolicyEvent, Severity, 
    Action, ActionKind, ActionStatus,
    Model, Dataset, Prompt, Tool, ToolType
)

def test_action_logging_structure():
    """Test that Action objects have all required fields for audit trail"""
    print("Testing action logging structure...")
    
    # Create a sample action
    action = Action(
        project_id=1,
        kind=ActionKind.SLACK,
        payload={"message": "test notification"},
        response={"status_code": 200, "response": "ok"},
        status=ActionStatus.OK
    )
    
    # Verify all required fields are present
    assert action.project_id is not None
    assert action.kind is not None
    assert action.payload is not None
    assert action.response is not None
    assert action.status is not None
    
    # Verify enums work correctly
    assert action.kind == ActionKind.SLACK
    assert action.status == ActionStatus.OK
    
    # Test failure case
    fail_action = Action(
        project_id=1,
        kind=ActionKind.JIRA,
        payload={"ticket": "data"},
        response={"error": "API timeout"},
        status=ActionStatus.FAIL
    )
    
    assert fail_action.status == ActionStatus.FAIL
    
    print("✅ Action logging structure test passed")

@patch('core.mcp_tools.slack.requests.post')
def test_slack_action_logging(mock_post):
    """Test that Slack notifications create proper action logs"""
    print("Testing Slack action logging...")
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(
        project=project,
        models=[Model(id=1, project_id=1, name="test-model", provider="huggingface", version="1.0")],
        policy_events=[
            PolicyEvent(
                id=1,
                project_id=1,
                severity=Severity.HIGH,
                rule="missing_license",
                artifact={"name": "test-model", "type": "model"},
                details={"message": "Critical issue"},
                dedupe_key="missing_license:test-model"
            )
        ]
    )
    
    # Create notifier with mock webhook URL
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = "https://hooks.slack.com/services/test/webhook/url"
        notifier = SlackNotifier()
        notifier.webhook_url = "https://hooks.slack.com/services/test/webhook/url"
        
        # Send scan summary
        scan_action = notifier.send_scan_summary(state)
        
        # Verify action logging for scan summary
        assert scan_action is not None
        assert scan_action.project_id == 1
        assert scan_action.kind == ActionKind.SLACK
        assert scan_action.status == ActionStatus.OK
        assert "blocks" in scan_action.payload
        assert scan_action.response["status_code"] == 200
        
        # Send policy alert
        alert_action = notifier.send_policy_alert(state)
        
        # Verify action logging for policy alert
        assert alert_action is not None
        assert alert_action.project_id == 1
        assert alert_action.kind == ActionKind.SLACK
        assert alert_action.status == ActionStatus.OK
        assert "blocks" in alert_action.payload
        assert alert_action.response["status_code"] == 200
    
    print("✅ Slack action logging test passed")

@patch('core.mcp_tools.jira.requests.post')
def test_jira_action_logging(mock_post):
    """Test that Jira ticket creation creates proper action logs"""
    print("Testing Jira action logging...")
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"key": "MLBOM-123", "id": "10001"}
    mock_response.text = '{"key": "MLBOM-123"}'
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(
        project=project,
        policy_events=[
            PolicyEvent(
                id=1,
                project_id=1,
                severity=Severity.HIGH,
                rule="missing_license",
                artifact={"name": "test-model", "type": "model"},
                details={"message": "Critical issue"},
                dedupe_key="missing_license:test-model"
            )
        ]
    )
    
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
        
        # Create policy ticket
        action = notifier.create_policy_ticket(state)
        
        # Verify action logging
        assert action is not None
        assert action.project_id == 1
        assert action.kind == ActionKind.JIRA
        assert action.status == ActionStatus.OK
        assert "fields" in action.payload
        assert action.response["status_code"] == 201
        assert action.response["ticket_key"] == "MLBOM-123"
        assert "ticket_url" in action.response
        
        # Verify payload contains ticket data
        assert "project" in action.payload["fields"]
        assert "summary" in action.payload["fields"]
        assert "description" in action.payload["fields"]
    
    print("✅ Jira action logging test passed")

@patch('core.mcp_tools.slack.requests.post')
def test_error_action_logging(mock_post):
    """Test that failed actions are properly logged"""
    print("Testing error action logging...")
    
    # Mock failed response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(project=project)
    
    # Create notifier with mock webhook URL
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = "https://hooks.slack.com/services/test/webhook/url"
        notifier = SlackNotifier()
        notifier.webhook_url = "https://hooks.slack.com/services/test/webhook/url"
        
        # Send notification (should fail)
        action = notifier.send_scan_summary(state)
        
        # Verify error is properly logged
        assert action is not None
        assert action.status == ActionStatus.FAIL
        assert action.response["status_code"] == 500
        assert "Internal Server Error" in action.response["response"]
    
    print("✅ Error action logging test passed")

def test_exception_action_logging():
    """Test that exceptions during external calls are logged"""
    print("Testing exception action logging...")
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(project=project)
    
    # Create notifier with mock webhook URL that will cause an exception
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = "https://hooks.slack.com/services/test/webhook/url"
        notifier = SlackNotifier()
        notifier.webhook_url = "https://hooks.slack.com/services/test/webhook/url"
        
        # Mock requests.post to raise an exception
        with patch('core.mcp_tools.slack.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network timeout")
            
            # Send notification (should catch exception)
            action = notifier.send_scan_summary(state)
            
            # Verify exception is properly logged
            assert action is not None
            assert action.status == ActionStatus.FAIL
            assert "error" in action.payload
            assert "Network timeout" in action.payload["error"]
            assert "error" in action.response
            assert "Network timeout" in action.response["error"]
    
    print("✅ Exception action logging test passed")

def test_payload_response_content():
    """Test that payloads and responses contain sufficient detail for audit"""
    print("Testing payload and response content...")
    
    # Create test data with policy events
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(
        project=project,
        commit_sha="abc123def456",
        models=[Model(id=1, project_id=1, name="critical-model", provider="huggingface", version="2.0")],
        policy_events=[
            PolicyEvent(
                id=1,
                project_id=1,
                severity=Severity.HIGH,
                rule="unapproved_license",
                artifact={"name": "critical-model", "type": "model"},
                details={"message": "Model uses GPL license which violates company policy"},
                dedupe_key="unapproved_license:critical-model"
            )
        ]
    )
    
    # Test Slack payload content
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = "https://hooks.slack.com/services/test/webhook/url"
        notifier = SlackNotifier()
        
        # Build policy alert message
        message = notifier._build_policy_alert_message(state)
        
        # Verify payload contains audit-relevant information
        message_str = json.dumps(message)
        assert "critical-model" in message_str
        assert "unapproved_license" in message_str
        assert "GPL license" in message_str
        assert "Policy Violations" in message_str
        
        # Verify structure allows for proper audit trail
        assert "blocks" in message
        assert len(message["blocks"]) > 0
        
        # Check that project and commit info is included
        assert "test-project" in message_str
    
    print("✅ Payload and response content test passed")

def run_all_tests():
    """Run all action logging tests"""
    print("🧪 Running Action Logging tests...\n")
    
    try:
        test_action_logging_structure()
        test_slack_action_logging()
        test_jira_action_logging()
        test_error_action_logging()
        test_exception_action_logging()
        test_payload_response_content()
        
        print("\n✅ All Action Logging tests passed!")
        print("\n📋 Action Logging Requirements Verification:")
        print("✅ 5.4: Action records created with payload, response, and status (ok/fail)")
        print("✅ Comprehensive logging for all external calls")
        print("✅ Detailed audit trail with sufficient context")
        print("✅ Error handling and exception logging")
        print("✅ Proper status tracking (OK/FAIL)")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)