import requests
import json
from typing import Dict, Any, Optional
from core.schemas.models import Action, ActionKind, ActionStatus, ScanState
from decouple import config
import logging

logger = logging.getLogger(__name__)

class SlackNotifier:
    """Sends notifications to Slack"""
    
    def __init__(self):
        self.webhook_url = config('SLACK_WEBHOOK_URL', default=None)
    
    def send_scan_summary(self, state: ScanState) -> Optional[Action]:
        """Send scan summary to Slack"""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return None
        
        try:
            # Build message
            message = self._build_scan_message(state)
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            # Create action record
            action = Action(
                project_id=state.project.id,
                kind=ActionKind.SLACK,
                payload=message,
                response={'status_code': response.status_code, 'response': response.text[:1000]},
                status=ActionStatus.OK if response.status_code == 200 else ActionStatus.FAIL
            )
            
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
            else:
                logger.error(f"Slack notification failed: {response.status_code} {response.text}")
            
            return action
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return Action(
                project_id=state.project.id,
                kind=ActionKind.SLACK,
                payload={'error': str(e)},
                response={'error': str(e)},
                status=ActionStatus.FAIL
            )
    
    def send_policy_alert(self, state: ScanState) -> Optional[Action]:
        """Send policy violations alert to Slack"""
        if not self.webhook_url or not state.policy_events:
            return None
        
        try:
            # Build alert message
            message = self._build_policy_alert_message(state)
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            # Create action record
            action = Action(
                project_id=state.project.id,
                kind=ActionKind.SLACK,
                payload=message,
                response={'status_code': response.status_code, 'response': response.text[:1000]},
                status=ActionStatus.OK if response.status_code == 200 else ActionStatus.FAIL
            )
            
            return action
            
        except Exception as e:
            logger.error(f"Failed to send Slack policy alert: {e}")
            return Action(
                project_id=state.project.id,
                kind=ActionKind.SLACK,
                payload={'error': str(e)},
                response={'error': str(e)},
                status=ActionStatus.FAIL
            )
    
    def _build_scan_message(self, state: ScanState) -> Dict[str, Any]:
        """Build Slack message for scan summary"""
        # Count components
        total_components = len(state.models) + len(state.datasets) + len(state.prompts) + len(state.tools)
        
        # Build blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔍 ML-BOM Scan Complete: {state.project.name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:* {state.project.name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Commit:* `{state.commit_sha[:8] if state.commit_sha else 'N/A'}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Components:* {total_components}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Policy Events:* {len(state.policy_events)}"
                    }
                ]
            }
        ]
        
        # Add component breakdown
        if total_components > 0:
            component_text = []
            if state.models:
                component_text.append(f"• {len(state.models)} Models")
            if state.datasets:
                component_text.append(f"• {len(state.datasets)} Datasets")
            if state.prompts:
                component_text.append(f"• {len(state.prompts)} Prompts")
            if state.tools:
                component_text.append(f"• {len(state.tools)} Tools")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Components Found:*\n{chr(10).join(component_text)}"
                }
            })
        
        # Add diff summary if available
        if state.diff and state.diff.summary.get('stats', {}).get('total_changes', 0) > 0:
            stats = state.diff.summary['stats']
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Changes from Previous Scan:*\n• {stats['additions']} additions\n• {stats['removals']} removals\n• {stats['modifications']} modifications"
                }
            })
        
        # Add policy events summary
        if state.policy_events:
            high_events = [e for e in state.policy_events if e.severity.value == 'high']
            medium_events = [e for e in state.policy_events if e.severity.value == 'medium']
            low_events = [e for e in state.policy_events if e.severity.value == 'low']
            
            severity_text = []
            if high_events:
                severity_text.append(f"🔴 {len(high_events)} High")
            if medium_events:
                severity_text.append(f"🟡 {len(medium_events)} Medium")
            if low_events:
                severity_text.append(f"🟢 {len(low_events)} Low")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Policy Events:*\n{' • '.join(severity_text)}"
                }
            })
        
        return {"blocks": blocks}
    
    def _build_policy_alert_message(self, state: ScanState) -> Dict[str, Any]:
        """Build Slack message for policy alerts"""
        high_events = [e for e in state.policy_events if e.severity.value == 'high']
        
        if not high_events:
            return self._build_scan_message(state)  # Fallback to scan summary
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Policy Violations: {state.project.name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(high_events)} high-severity policy violations detected*"
                }
            }
        ]
        
        # Add top violations
        for i, event in enumerate(high_events[:5]):  # Show max 5
            artifact_name = event.artifact.get('name', 'Unknown')
            artifact_type = event.artifact.get('type', 'component')
            message = event.details.get('message', event.rule)
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i+1}. {event.rule}*\n{artifact_type.title()}: `{artifact_name}`\n{message}"
                }
            })
        
        if len(high_events) > 5:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_... and {len(high_events) - 5} more violations_"
                }
            })
        
        return {"blocks": blocks}