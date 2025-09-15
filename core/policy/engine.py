import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from core.schemas.models import ScanState, PolicyEvent, Severity, Policy
from core.db.connection import db_manager
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class PolicyEngine:
    """Evaluates policy rules against scan results"""
    
    def __init__(self):
        self.rules = {
            'missing_license': self._check_missing_license,
            'unapproved_license': self._check_unapproved_license,
            'unknown_provider': self._check_unknown_provider,
            'model_bump_major': self._check_model_bump_major,
            'prompt_changed_protected_path': self._check_prompt_changed_protected_path
        }
    
    def evaluate_policies(self, state: ScanState) -> ScanState:
        """Evaluate all policies against scan state"""
        try:
            # Get active policies
            policies = self._get_active_policies()
            
            # Get policy overrides for this project
            overrides = self._get_policy_overrides(state.project.id)
            
            # Evaluate each policy
            for policy in policies:
                if policy.rule in overrides:
                    logger.info(f"Policy {policy.rule} overridden for project {state.project.id}")
                    continue
                
                if policy.rule in self.rules:
                    events = self.rules[policy.rule](state, policy)
                    
                    # Deduplicate and store events
                    for event in events:
                        if not self._is_duplicate_event(event):
                            stored_event = self._store_policy_event(event)
                            state.policy_events.append(stored_event)
            
            logger.info(f"Generated {len(state.policy_events)} policy events")
            
        except Exception as e:
            logger.error(f"Failed to evaluate policies: {e}")
            state.error = str(e)
        
        return state
    
    def _get_active_policies(self) -> List[Policy]:
        """Get all active policies"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, rule, severity, spec
                FROM policies
            """))
            
            policies = []
            for row in result:
                policies.append(Policy(
                    id=row.id,
                    rule=row.rule,
                    severity=Severity(row.severity),
                    spec=json.loads(row.spec) if row.spec else {}
                ))
            
            return policies
    
    def _get_policy_overrides(self, project_id: int) -> Dict[str, datetime]:
        """Get active policy overrides for a project"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT rule, expiration_date
                FROM policy_overrides
                WHERE project_id = :project_id AND expiration_date > NOW()
            """), {'project_id': project_id})
            
            return {row.rule: row.expiration_date for row in result}
    
    def _check_missing_license(self, state: ScanState, policy: Policy) -> List[PolicyEvent]:
        """Check for artifacts without licenses"""
        events = []
        
        # Check models
        for model in state.models:
            if not model.license:
                events.append(PolicyEvent(
                    project_id=state.project.id,
                    severity=policy.severity,
                    rule=policy.rule,
                    artifact={
                        'type': 'model',
                        'name': model.name,
                        'provider': model.provider,
                        'version': model.version
                    },
                    details={'message': f'Model {model.name} has no license'},
                    dedupe_key=self._generate_dedupe_key(policy.rule, 'model', model.name)
                ))
        
        # Check datasets
        for dataset in state.datasets:
            if not dataset.license:
                events.append(PolicyEvent(
                    project_id=state.project.id,
                    severity=policy.severity,
                    rule=policy.rule,
                    artifact={
                        'type': 'dataset',
                        'name': dataset.name,
                        'version': dataset.version
                    },
                    details={'message': f'Dataset {dataset.name} has no license'},
                    dedupe_key=self._generate_dedupe_key(policy.rule, 'dataset', dataset.name)
                ))
        
        return events
    
    def _check_unapproved_license(self, state: ScanState, policy: Policy) -> List[PolicyEvent]:
        """Check for unapproved licenses"""
        events = []
        allowed_licenses = policy.spec.get('allowed_licenses', [])
        
        # Check models
        for model in state.models:
            if model.license and model.license not in allowed_licenses:
                events.append(PolicyEvent(
                    project_id=state.project.id,
                    severity=policy.severity,
                    rule=policy.rule,
                    artifact={
                        'type': 'model',
                        'name': model.name,
                        'provider': model.provider,
                        'version': model.version,
                        'license': model.license
                    },
                    details={
                        'message': f'Model {model.name} has unapproved license: {model.license}',
                        'allowed_licenses': allowed_licenses
                    },
                    dedupe_key=self._generate_dedupe_key(policy.rule, 'model', model.name, model.license)
                ))
        
        # Check datasets
        for dataset in state.datasets:
            if dataset.license and dataset.license not in allowed_licenses:
                events.append(PolicyEvent(
                    project_id=state.project.id,
                    severity=policy.severity,
                    rule=policy.rule,
                    artifact={
                        'type': 'dataset',
                        'name': dataset.name,
                        'version': dataset.version,
                        'license': dataset.license
                    },
                    details={
                        'message': f'Dataset {dataset.name} has unapproved license: {dataset.license}',
                        'allowed_licenses': allowed_licenses
                    },
                    dedupe_key=self._generate_dedupe_key(policy.rule, 'dataset', dataset.name, dataset.license)
                ))
        
        return events
    
    def _check_unknown_provider(self, state: ScanState, policy: Policy) -> List[PolicyEvent]:
        """Check for unknown providers"""
        events = []
        
        for model in state.models:
            if model.provider == 'unknown' or not model.source_url:
                events.append(PolicyEvent(
                    project_id=state.project.id,
                    severity=policy.severity,
                    rule=policy.rule,
                    artifact={
                        'type': 'model',
                        'name': model.name,
                        'provider': model.provider,
                        'version': model.version
                    },
                    details={'message': f'Model {model.name} has unknown provider or missing source URL'},
                    dedupe_key=self._generate_dedupe_key(policy.rule, 'model', model.name)
                ))
        
        return events
    
    def _check_model_bump_major(self, state: ScanState, policy: Policy) -> List[PolicyEvent]:
        """Check for major version bumps in models"""
        events = []
        
        if not state.diff:
            return events
        
        # Look for version changes in diff
        for change in state.diff.summary.get('changes', []):
            if (change.get('type') == 'modification' and 
                change.get('field') == 'version' and
                self._is_major_version_bump(change.get('old_value'), change.get('new_value'))):
                
                events.append(PolicyEvent(
                    project_id=state.project.id,
                    severity=policy.severity,
                    rule=policy.rule,
                    artifact={
                        'type': 'model',
                        'component_id': change.get('component_id'),
                        'component_name': change.get('component_name')
                    },
                    details={
                        'message': f'Major version bump detected: {change.get("old_value")} → {change.get("new_value")}',
                        'old_version': change.get('old_value'),
                        'new_version': change.get('new_value')
                    },
                    dedupe_key=self._generate_dedupe_key(policy.rule, 'version_bump', 
                                                       change.get('component_id'))
                ))
        
        return events
    
    def _check_prompt_changed_protected_path(self, state: ScanState, policy: Policy) -> List[PolicyEvent]:
        """Check for prompt changes in protected paths"""
        events = []
        protected_paths = policy.spec.get('protected_paths', ['/prompts/', '/prod/'])
        
        if not state.diff:
            return events
        
        # Look for prompt changes in protected paths
        for change in state.diff.summary.get('changes', []):
            if change.get('type') == 'modification' and change.get('field') == 'property.blob_sha':
                # This is a prompt content change
                component_name = change.get('component_name', '')
                
                # Check if in protected path
                for prompt in state.prompts:
                    if (prompt.name == component_name and 
                        any(protected in prompt.path for protected in protected_paths)):
                        
                        events.append(PolicyEvent(
                            project_id=state.project.id,
                            severity=policy.severity,
                            rule=policy.rule,
                            artifact={
                                'type': 'prompt',
                                'name': prompt.name,
                                'path': prompt.path
                            },
                            details={
                                'message': f'Prompt {prompt.name} changed in protected path {prompt.path}',
                                'old_sha': change.get('old_value'),
                                'new_sha': change.get('new_value')
                            },
                            dedupe_key=self._generate_dedupe_key(policy.rule, 'prompt', prompt.name, prompt.path)
                        ))
        
        return events
    
    def _is_major_version_bump(self, old_version: str, new_version: str) -> bool:
        """Check if version change is a major bump"""
        try:
            if not old_version or not new_version:
                return False
            
            # Remove 'v' prefix if present
            old_clean = old_version.lstrip('v')
            new_clean = new_version.lstrip('v')
            
            old_parts = old_clean.split('.')
            new_parts = new_clean.split('.')
            
            if len(old_parts) > 0 and len(new_parts) > 0:
                old_major = int(old_parts[0])
                new_major = int(new_parts[0])
                return new_major > old_major
        except (ValueError, IndexError):
            pass
        
        return False
    
    def _generate_dedupe_key(self, rule: str, *args) -> str:
        """Generate deduplication key for policy event"""
        key_parts = [rule] + [str(arg) for arg in args]
        key_string = ':'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_duplicate_event(self, event: PolicyEvent) -> bool:
        """Check if event is a duplicate within 24 hours"""
        with db_manager.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            result = session.execute(text("""
                SELECT COUNT(*) as count
                FROM policy_events
                WHERE project_id = :project_id
                AND dedupe_key = :dedupe_key
                AND created_at > :cutoff_time
            """), {
                'project_id': event.project_id,
                'dedupe_key': event.dedupe_key,
                'cutoff_time': cutoff_time
            }).fetchone()
            
            return result.count > 0
    
    def _store_policy_event(self, event: PolicyEvent) -> PolicyEvent:
        """Store policy event in database"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                INSERT INTO policy_events 
                (project_id, severity, rule, artifact, details, dedupe_key, created_at)
                VALUES (:project_id, :severity, :rule, :artifact, :details, :dedupe_key, :created_at)
            """), {
                'project_id': event.project_id,
                'severity': event.severity.value,
                'rule': event.rule,
                'artifact': json.dumps(event.artifact),
                'details': json.dumps(event.details),
                'dedupe_key': event.dedupe_key,
                'created_at': datetime.utcnow()
            })
            
            session.commit()
            
            event.id = result.lastrowid
            event.created_at = datetime.utcnow()
            
            return event
    
    def get_project_events(self, project_id: int, limit: int = 50) -> List[PolicyEvent]:
        """Get recent policy events for a project"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, project_id, severity, rule, artifact, details, dedupe_key, created_at
                FROM policy_events
                WHERE project_id = :project_id
                ORDER BY created_at DESC
                LIMIT :limit
            """), {
                'project_id': project_id,
                'limit': limit
            })
            
            events = []
            for row in result:
                events.append(PolicyEvent(
                    id=row.id,
                    project_id=row.project_id,
                    severity=Severity(row.severity),
                    rule=row.rule,
                    artifact=json.loads(row.artifact),
                    details=json.loads(row.details),
                    dedupe_key=row.dedupe_key,
                    created_at=row.created_at
                ))
            
            return events