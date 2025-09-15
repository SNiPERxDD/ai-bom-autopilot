#!/usr/bin/env python3
"""
Test script for SlackNotifier functionality
"""

import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.mcp_tools.slack import SlackNotifier
from core.schemas.models import (
    ScanState, Project, PolicyEvent, Severity, 
    BOMDiff, Action, ActionKind, ActionStatus,
    Model, Dataset, Prompt, Tool, ToolType
)

def test_slack_blocks_construction():
    """Test that Slack blocks are properly constructed"""
    print("Testing Slack blocks construction...")
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(
        project=project,
        commit_sha="abc123def456",
        models=[Model(id=1, project_id=1, name="test-model", provider="huggingface", version="1.0")],
        datasets=[Dataset(id=1, project_id=1, name="test-dataset", version="1.0")],
        prompts=[Prompt(id=1, project_id=1, name="test-prompt", version="1.0", path="/prompts/test.txt", blob_sha="abc123")],
        tools=[Tool(id=1, project_id=1, name="test-tool", version="1.0", type=ToolType.LIB)],
        policy_events=[
            PolicyEvent(
                id=1,
                project_id=1,
                severity=Severity.HIGH,
                rule="missing_license",
                artifact={"name": "test-model", "type": "model"},
                details={"message": "Model is missing license information"},
                dedupe_key="missing_license:test-model"
            )
        ]
    )
    
    # Create SlackNotifier
    notifier = SlackNotifier()
    
    # Test scan message construction
    scan_message = notifier._build_scan_message(state)
    
    # Verify structure
    assert "blocks" in scan_message
    assert len(scan_message["blocks"]) > 0
    
    # Check header block
    header_block = scan_message["blocks"][0]
    assert header_block["type"] == "header"
    assert "test-project" in header_block["text"]["text"]
    
    # Check that components are mentioned
    message_text = json.dumps(scan_message)
    assert "1 Models" in message_text
    assert "1 Datasets" in message_text
    assert "1 Prompts" in message_text
    assert "1 Tools" in message_text
    
    print("✅ Slack blocks construction test passed")

def test_policy_alert_construction():
    """Test policy alert message construction"""
    print("Testing policy alert construction...")
    
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(
        project=project,
        policy_events=[
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
    )
    
    notifier = SlackNotifier()
    alert_message = notifier._build_policy_alert_message(state)
    
    # Verify structure
    assert "blocks" in alert_message
    
    # Check that it's formatted as an alert
    message_text = json.dumps(alert_message)
    assert "Policy Violations" in message_text
    assert "missing_license" in message_text
    assert "unapproved_license" in message_text
    assert "dangerous-model" in message_text
    assert "restricted-dataset" in message_text
    
    print("✅ Policy alert construction test passed")

@patch('core.mcp_tools.slack.requests.post')
def test_webhook_posting(mock_post):
    """Test webhook POST functionality"""
    print("Testing webhook POST...")
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(project=project)
    
    # Create notifier with mock webhook URL
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = "https://hooks.slack.com/services/test/webhook/url"
        notifier = SlackNotifier()
        notifier.webhook_url = "https://hooks.slack.com/services/test/webhook/url"
        
        # Send notification
        action = notifier.send_scan_summary(state)
        
        # Verify POST was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert call_args[1]['json'] is not None
        assert call_args[1]['timeout'] == 10
        
        # Check action record
        assert action is not None
        assert action.kind == ActionKind.SLACK
        assert action.status == ActionStatus.OK
        assert action.project_id == 1
        assert "blocks" in action.payload
    
    print("✅ Webhook POST test passed")

@patch('core.mcp_tools.slack.requests.post')
def test_error_handling(mock_post):
    """Test error handling for failed webhook calls"""
    print("Testing error handling...")
    
    # Mock failed response
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response
    
    # Create test data
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(project=project)
    
    # Create notifier with mock webhook URL
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = "https://hooks.slack.com/services/test/webhook/url"
        notifier = SlackNotifier()
        notifier.webhook_url = "https://hooks.slack.com/services/test/webhook/url"
        
        # Send notification
        action = notifier.send_scan_summary(state)
        
        # Check action record shows failure
        assert action is not None
        assert action.status == ActionStatus.FAIL
        assert action.response['status_code'] == 400
    
    print("✅ Error handling test passed")

def test_no_webhook_configured():
    """Test behavior when no webhook URL is configured"""
    print("Testing no webhook configured...")
    
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(project=project)
    
    # Create notifier without webhook URL
    with patch('core.mcp_tools.slack.config') as mock_config:
        mock_config.return_value = None
        notifier = SlackNotifier()
        
        # Send notification
        action = notifier.send_scan_summary(state)
        
        # Should return None when not configured
        assert action is None
    
    print("✅ No webhook configured test passed")

def run_all_tests():
    """Run all SlackNotifier tests"""
    print("🧪 Running SlackNotifier tests...\n")
    
    try:
        test_slack_blocks_construction()
        test_policy_alert_construction()
        test_webhook_posting()
        test_error_handling()
        test_no_webhook_configured()
        
        print("\n✅ All SlackNotifier tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)