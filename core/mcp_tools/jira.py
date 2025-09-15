import requests
import json
import base64
from typing import Dict, Any, Optional
from core.schemas.models import Action, ActionKind, ActionStatus, ScanState
from decouple import config
import logging

logger = logging.getLogger(__name__)

class JiraNotifier:
    """Creates Jira tickets for policy violations"""
    
    def __init__(self):
        self.jira_url = config('JIRA_URL', default=None)
        self.username = config('JIRA_USERNAME', default=None)
        self.api_token = config('JIRA_API_TOKEN', default=None)
        self.project_key = config('JIRA_PROJECT_KEY', default='MLBOM')
        
        if self.username and self.api_token:
            # Create basic auth header
            auth_string = f"{self.username}:{self.api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self.headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/json'
            }
        else:
            self.headers = None
    
    def create_policy_ticket(self, state: ScanState) -> Optional[Action]:
        """Create Jira ticket for policy violations"""
        if not self._is_configured() or not state.policy_events:
            return None
        
        # Only create tickets for high-severity events
        high_events = [e for e in state.policy_events if e.severity.value == 'high']
        if not high_events:
            return None
        
        try:
            # Build ticket payload
            ticket_data = self._build_ticket_data(state, high_events)
            
            # Create ticket
            response = requests.post(
                f"{self.jira_url}/rest/api/3/issue",
                headers=self.headers,
                json=ticket_data,
                timeout=30
            )
            
            # Create action record
            action = Action(
                project_id=state.project.id,
                kind=ActionKind.JIRA,
                payload=ticket_data,
                response={
                    'status_code': response.status_code,
                    'response': response.text[:1000]
                },
                status=ActionStatus.OK if response.status_code == 201 else ActionStatus.FAIL
            )
            
            if response.status_code == 201:
                ticket_info = response.json()
                action.response['ticket_key'] = ticket_info.get('key')
                action.response['ticket_url'] = f"{self.jira_url}/browse/{ticket_info.get('key')}"
                logger.info(f"Jira ticket created: {ticket_info.get('key')}")
            else:
                logger.error(f"Jira ticket creation failed: {response.status_code} {response.text}")
            
            return action
            
        except Exception as e:
            logger.error(f"Failed to create Jira ticket: {e}")
            return Action(
                project_id=state.project.id,
                kind=ActionKind.JIRA,
                payload={'error': str(e)},
                response={'error': str(e)},
                status=ActionStatus.FAIL
            )
    
    def create_scan_summary_ticket(self, state: ScanState) -> Optional[Action]:
        """Create Jira ticket with scan summary"""
        if not self._is_configured():
            return None
        
        try:
            # Build ticket payload
            ticket_data = self._build_summary_ticket_data(state)
            
            # Create ticket
            response = requests.post(
                f"{self.jira_url}/rest/api/3/issue",
                headers=self.headers,
                json=ticket_data,
                timeout=30
            )
            
            # Create action record
            action = Action(
                project_id=state.project.id,
                kind=ActionKind.JIRA,
                payload=ticket_data,
                response={
                    'status_code': response.status_code,
                    'response': response.text[:1000]
                },
                status=ActionStatus.OK if response.status_code == 201 else ActionStatus.FAIL
            )
            
            if response.status_code == 201:
                ticket_info = response.json()
                action.response['ticket_key'] = ticket_info.get('key')
                action.response['ticket_url'] = f"{self.jira_url}/browse/{ticket_info.get('key')}"
                logger.info(f"Jira summary ticket created: {ticket_info.get('key')}")
            
            return action
            
        except Exception as e:
            logger.error(f"Failed to create Jira summary ticket: {e}")
            return Action(
                project_id=state.project.id,
                kind=ActionKind.JIRA,
                payload={'error': str(e)},
                response={'error': str(e)},
                status=ActionStatus.FAIL
            )
    
    def _is_configured(self) -> bool:
        """Check if Jira is properly configured"""
        return all([self.jira_url, self.username, self.api_token, self.headers])
    
    def _build_ticket_data(self, state: ScanState, high_events) -> Dict[str, Any]:
        """Build Jira ticket data for policy violations"""
        # Build description
        description_lines = [
            f"ML-BOM scan of project *{state.project.name}* detected {len(high_events)} high-severity policy violations.",
            "",
            f"*Scan Details:*",
            f"• Project: {state.project.name}",
            f"• Repository: {state.project.repo_url}",
            f"• Commit: {state.commit_sha[:8] if state.commit_sha else 'N/A'}",
            f"• Total Components: {len(state.models) + len(state.datasets) + len(state.prompts) + len(state.tools)}",
            "",
            "*Policy Violations:*"
        ]
        
        for i, event in enumerate(high_events[:10], 1):  # Limit to 10 events
            artifact_name = event.artifact.get('name', 'Unknown')
            artifact_type = event.artifact.get('type', 'component')
            message = event.details.get('message', event.rule)
            
            description_lines.extend([
                f"{i}. *{event.rule}*",
                f"   • {artifact_type.title()}: {artifact_name}",
                f"   • {message}",
                ""
            ])
        
        if len(high_events) > 10:
            description_lines.append(f"... and {len(high_events) - 10} more violations")
        
        return {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"ML-BOM Policy Violations: {state.project.name}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "\n".join(description_lines)
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
                "labels": ["ml-bom", "policy-violation", "automated"]
            }
        }
    
    def _build_summary_ticket_data(self, state: ScanState) -> Dict[str, Any]:
        """Build Jira ticket data for scan summary"""
        # Build description
        description_lines = [
            f"ML-BOM scan completed for project *{state.project.name}*.",
            "",
            f"*Scan Results:*",
            f"• Project: {state.project.name}",
            f"• Repository: {state.project.repo_url}",
            f"• Commit: {state.commit_sha[:8] if state.commit_sha else 'N/A'}",
            f"• Models: {len(state.models)}",
            f"• Datasets: {len(state.datasets)}",
            f"• Prompts: {len(state.prompts)}",
            f"• Tools: {len(state.tools)}",
            f"• Policy Events: {len(state.policy_events)}",
            ""
        ]
        
        # Add diff summary if available
        if state.diff and state.diff.summary.get('stats', {}).get('total_changes', 0) > 0:
            stats = state.diff.summary['stats']
            description_lines.extend([
                "*Changes from Previous Scan:*",
                f"• Additions: {stats['additions']}",
                f"• Removals: {stats['removals']}",
                f"• Modifications: {stats['modifications']}",
                ""
            ])
        
        # Add policy events summary
        if state.policy_events:
            high_events = [e for e in state.policy_events if e.severity.value == 'high']
            medium_events = [e for e in state.policy_events if e.severity.value == 'medium']
            low_events = [e for e in state.policy_events if e.severity.value == 'low']
            
            description_lines.extend([
                "*Policy Events by Severity:*",
                f"• High: {len(high_events)}",
                f"• Medium: {len(medium_events)}",
                f"• Low: {len(low_events)}",
                ""
            ])
        
        # Determine priority based on policy events
        priority = "Medium"
        if any(e.severity.value == 'high' for e in state.policy_events):
            priority = "High"
        elif not state.policy_events:
            priority = "Low"
        
        return {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"ML-BOM Scan Summary: {state.project.name}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "\n".join(description_lines)
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Task"},
                "priority": {"name": priority},
                "labels": ["ml-bom", "scan-summary", "automated"]
            }
        }