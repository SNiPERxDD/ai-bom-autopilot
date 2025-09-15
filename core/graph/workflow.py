from langgraph.graph import StateGraph, END
from typing import Dict, Any, Optional
from core.schemas.models import ScanState, Project
from core.scan_git.scanner import GitScanner
from core.scan_hf.fetcher import HuggingFaceFetcher
from core.normalize.classifier import ArtifactClassifier
from core.embeddings.embedder import EmbeddingService
from core.bom.generator import BOMGenerator
from core.diff.engine import DiffEngine
from core.policy.engine import PolicyEngine
from core.mcp_tools.slack import SlackNotifier
from core.mcp_tools.jira import JiraNotifier
from core.runtime.collector import RuntimeCollector, RuntimeIntegration
from core.db.connection import db_manager
from sqlalchemy import text
import logging
import time
import os
from functools import wraps

logger = logging.getLogger(__name__)

def timeout_node(timeout_seconds: int = 300):
    """Decorator to add timeout to workflow nodes"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Node {func.__name__} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    logger.error(f"Node {func.__name__} timed out after {elapsed:.2f}s")
                    raise TimeoutError(f"Node {func.__name__} timed out after {timeout_seconds}s")
                else:
                    logger.error(f"Node {func.__name__} failed after {elapsed:.2f}s: {e}")
                    raise
        return wrapper
    return decorator

def retry_node(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator to add retry logic to workflow nodes"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Node {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Node {func.__name__} failed after {max_retries + 1} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator

class MLBOMWorkflow:
    """LangGraph workflow for ML-BOM generation"""
    
    def __init__(self):
        self.git_scanner = GitScanner()
        self.hf_fetcher = HuggingFaceFetcher()
        self.classifier = ArtifactClassifier()
        self.embedder = EmbeddingService()
        self.bom_generator = BOMGenerator()
        self.diff_engine = DiffEngine()
        self.policy_engine = PolicyEngine()
        self.slack_notifier = SlackNotifier()
        self.jira_notifier = JiraNotifier()
        
        # Configuration
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        self.allowed_tools = {'slack', 'jira'}  # Tool allowlist
        self.runtime_enabled = os.getenv('RUNTIME_TRACING', 'true').lower() == 'true'
        self.runtime_duration = int(os.getenv('RUNTIME_DURATION', '30'))  # seconds
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ScanState)
        
        # Add nodes in the correct order: ScanPlan → ScanGit → ScanHF → RuntimeCollect → Normalize → Embed+Index → BOMGen → DiffPrev → PolicyCheck → Notify → End
        workflow.add_node("scan_plan", self._scan_plan_node)
        workflow.add_node("scan_git", self._scan_git_node)
        workflow.add_node("scan_hf", self._scan_hf_node)
        
        # Add runtime collection node (conditional)
        if self.runtime_enabled:
            workflow.add_node("runtime_collect", self._runtime_collect_node)
        
        workflow.add_node("normalize", self._normalize_node)
        workflow.add_node("embed_index", self._embed_index_node)
        workflow.add_node("generate_bom", self._generate_bom_node)
        workflow.add_node("diff_previous", self._diff_previous_node)
        workflow.add_node("check_policies", self._check_policies_node)
        workflow.add_node("notify", self._notify_node)
        
        # Add edges
        workflow.add_edge("scan_plan", "scan_git")
        workflow.add_edge("scan_git", "scan_hf")
        
        if self.runtime_enabled:
            workflow.add_edge("scan_hf", "runtime_collect")
            workflow.add_edge("runtime_collect", "normalize")
        else:
            workflow.add_edge("scan_hf", "normalize")
        
        workflow.add_edge("normalize", "embed_index")
        workflow.add_edge("embed_index", "generate_bom")
        workflow.add_edge("generate_bom", "diff_previous")
        workflow.add_edge("diff_previous", "check_policies")
        workflow.add_edge("check_policies", "notify")
        workflow.add_edge("notify", END)
        
        # Set entry point
        workflow.set_entry_point("scan_plan")
        
        return workflow.compile()
    
    def run_scan(self, project: Project, dry_run: bool = False) -> ScanState:
        """Run the complete ML-BOM scan workflow"""
        logger.info(f"Starting ML-BOM scan for project: {project.name} (dry_run={dry_run})")
        
        # Initialize state
        initial_state = ScanState(project=project)
        initial_state.meta['dry_run'] = dry_run
        
        try:
            # Run the workflow
            result = self.workflow.invoke(initial_state)
            
            logger.info(f"ML-BOM scan completed for project: {project.name}")
            return result
            
        except Exception as e:
            logger.error(f"ML-BOM scan failed for project {project.name}: {e}")
            initial_state.error = str(e)
            return initial_state
    
    @timeout_node(timeout_seconds=60)
    @retry_node(max_retries=2)
    def _scan_plan_node(self, state: ScanState) -> ScanState:
        """Initialize scan plan and validate project configuration"""
        logger.info("Planning scan...")
        try:
            # Validate project configuration
            if not state.project.repo_url:
                raise ValueError("Project repo_url is required")
            
            # Set scan metadata
            state.meta['scan_start_time'] = time.time()
            state.meta['workflow_version'] = '1.0'
            
            # Initialize counters
            state.meta['counters'] = {
                'files_scanned': 0,
                'hf_cards_fetched': 0,
                'artifacts_normalized': 0,
                'chunks_embedded': 0
            }
            
            logger.info(f"Scan plan initialized for project: {state.project.name}")
            return state
            
        except Exception as e:
            logger.error(f"Scan planning failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=300)
    @retry_node(max_retries=2)
    def _scan_git_node(self, state: ScanState) -> ScanState:
        """Scan Git repository for ML artifacts"""
        logger.info("Scanning Git repository...")
        try:
            return self.git_scanner.scan_project_repository(state.project)
        except Exception as e:
            logger.error(f"Git scan failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=180)
    @retry_node(max_retries=3)
    def _scan_hf_node(self, state: ScanState) -> ScanState:
        """Fetch HuggingFace model/dataset cards"""
        logger.info("Fetching HuggingFace cards...")
        try:
            if state.hf_slugs:
                hf_cards = self.hf_fetcher.batch_fetch_cards(state.hf_slugs)
                # Store cards in state for normalization
                state.meta['hf_cards'] = hf_cards
            return state
        except Exception as e:
            logger.error(f"HF scan failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=120)
    @retry_node(max_retries=2)
    def _runtime_collect_node(self, state: ScanState) -> ScanState:
        """Collect runtime AI/ML artifact usage"""
        logger.info(f"Starting runtime collection for {self.runtime_duration} seconds...")
        dry_run = state.meta.get('dry_run', False)
        
        try:
            if dry_run:
                logger.info("DRY_RUN mode: Skipping runtime collection")
                state.meta['runtime_artifacts'] = []
                return state
            
            # Initialize runtime collector
            collector = RuntimeCollector(state.project.id)
            
            # Start collection
            if not collector.start_collection():
                logger.warning("Failed to start runtime collection, continuing without runtime data")
                state.meta['runtime_artifacts'] = []
                return state
            
            logger.info(f"Runtime collection started. Waiting {self.runtime_duration} seconds...")
            logger.info("Please run your ML application now to capture runtime artifact usage.")
            
            # Wait for the specified duration
            time.sleep(self.runtime_duration)
            
            # Stop collection and get artifacts
            runtime_artifacts = collector.stop_collection()
            
            # Store runtime artifacts in state
            state.meta['runtime_artifacts'] = runtime_artifacts
            state.meta['counters']['runtime_artifacts'] = len(runtime_artifacts)
            
            logger.info(f"Runtime collection completed. Captured {len(runtime_artifacts)} unique artifacts.")
            
            # Get collection summary
            summary = collector.get_collection_summary()
            state.meta['runtime_summary'] = summary
            
            return state
            
        except Exception as e:
            logger.error(f"Runtime collection failed: {e}")
            # Don't fail the entire workflow, just continue without runtime data
            state.meta['runtime_artifacts'] = []
            state.meta['runtime_error'] = str(e)
            return state
    
    @timeout_node(timeout_seconds=240)
    @retry_node(max_retries=2)
    def _normalize_node(self, state: ScanState) -> ScanState:
        """Normalize and classify artifacts (static + runtime)"""
        logger.info("Normalizing artifacts...")
        try:
            hf_cards = state.meta.get('hf_cards', {})
            
            # First normalize static artifacts
            state = self.classifier.normalize_artifacts(state, hf_cards)
            
            # Then add runtime artifacts if available
            runtime_artifacts = state.meta.get('runtime_artifacts', [])
            if runtime_artifacts:
                logger.info(f"Adding {len(runtime_artifacts)} runtime artifacts to normalized artifacts")
                
                # Combine static and runtime artifacts, deduplicating by ID
                all_artifacts = list(state.normalized_artifacts) + runtime_artifacts
                
                # Deduplicate by canonical ID, preferring runtime versions
                seen_ids = set()
                unique_artifacts = []
                
                for artifact in all_artifacts:
                    if artifact.id not in seen_ids:
                        unique_artifacts.append(artifact)
                        seen_ids.add(artifact.id)
                    else:
                        # If we have both static and runtime versions, prefer runtime
                        if artifact.metadata and artifact.metadata.get('runtime_detected'):
                            # Replace static version with runtime version
                            for i, existing in enumerate(unique_artifacts):
                                if existing.id == artifact.id:
                                    unique_artifacts[i] = artifact
                                    break
                
                state.normalized_artifacts = unique_artifacts
                logger.info(f"Combined artifacts: {len(unique_artifacts)} unique artifacts total")
            
            return state
            
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=600)
    @retry_node(max_retries=2)
    def _embed_index_node(self, state: ScanState) -> ScanState:
        """Create embeddings and index evidence"""
        logger.info("Creating embeddings...")
        try:
            return self.embedder.process_evidence(state)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=120)
    @retry_node(max_retries=2)
    def _generate_bom_node(self, state: ScanState) -> ScanState:
        """Generate CycloneDX ML-BOM"""
        logger.info("Generating BOM...")
        dry_run = state.meta.get('dry_run', False)
        
        try:
            if dry_run:
                logger.info("DRY_RUN mode: Generating BOM without database storage")
            return self.bom_generator.generate_bom(state)
        except Exception as e:
            logger.error(f"BOM generation failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=120)
    @retry_node(max_retries=2)
    def _diff_previous_node(self, state: ScanState) -> ScanState:
        """Compare with previous BOM"""
        logger.info("Generating diff...")
        dry_run = state.meta.get('dry_run', False)
        
        try:
            if dry_run:
                logger.info("DRY_RUN mode: Generating diff without database storage")
            return self.diff_engine.generate_diff(state)
        except Exception as e:
            logger.error(f"Diff generation failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=180)
    @retry_node(max_retries=2)
    def _check_policies_node(self, state: ScanState) -> ScanState:
        """Evaluate policy rules"""
        logger.info("Checking policies...")
        dry_run = state.meta.get('dry_run', False)
        
        try:
            if dry_run:
                logger.info("DRY_RUN mode: Evaluating policies without database storage")
            return self.policy_engine.evaluate_policies(state)
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            state.error = str(e)
            return state
    
    @timeout_node(timeout_seconds=120)
    def _notify_node(self, state: ScanState) -> ScanState:
        """Send notifications"""
        logger.info("Sending notifications...")
        dry_run = state.meta.get('dry_run', False)
        
        try:
            # Check if notifications should be sent
            if dry_run:
                logger.info("DRY_RUN mode: Skipping external notifications")
                return state
            
            # Send Slack notification (if allowed)
            if 'slack' in self.allowed_tools:
                slack_action = self.slack_notifier.send_scan_summary(state)
                if slack_action:
                    self._store_action(slack_action, dry_run)
                    state.actions.append(slack_action)
            else:
                logger.warning("Slack notifications not in allowed tools list")
            
            # Send policy alert if there are high-severity events
            high_events = [e for e in state.policy_events if e.severity.value == 'high']
            if high_events:
                if 'slack' in self.allowed_tools:
                    slack_alert = self.slack_notifier.send_policy_alert(state)
                    if slack_alert:
                        self._store_action(slack_alert, dry_run)
                        state.actions.append(slack_alert)
                
                # Create Jira ticket for high-severity events (if allowed)
                if 'jira' in self.allowed_tools:
                    jira_action = self.jira_notifier.create_policy_ticket(state)
                    if jira_action:
                        self._store_action(jira_action, dry_run)
                        state.actions.append(jira_action)
                else:
                    logger.warning("Jira notifications not in allowed tools list")
            
            return state
            
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            state.error = str(e)
            return state
    
    def _store_action(self, action, dry_run: bool = False):
        """Store action in database"""
        if dry_run:
            logger.info(f"DRY_RUN mode: Would store action {action.kind.value}")
            return
            
        try:
            with db_manager.get_session() as session:
                result = session.execute(text("""
                    INSERT INTO actions (project_id, kind, payload, response, status, created_at)
                    VALUES (:project_id, :kind, :payload, :response, :status, NOW())
                """), {
                    'project_id': action.project_id,
                    'kind': action.kind.value,
                    'payload': str(action.payload).replace("'", '"'),
                    'response': str(action.response).replace("'", '"'),
                    'status': action.status.value
                })
                session.commit()
                action.id = result.lastrowid
        except Exception as e:
            logger.warning(f"Failed to store action: {e}")
    
    def should_skip_diff(self, state: ScanState) -> bool:
        """Determine if diff should be skipped (e.g., first BOM)"""
        try:
            with db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT COUNT(*) as count FROM boms WHERE project_id = :project_id
                """), {'project_id': state.project.id}).fetchone()
                
                return result.count <= 1  # Skip if this is the first or second BOM
        except Exception as e:
            logger.warning(f"Failed to check BOM count: {e}")
            return False
    
    def should_skip_notifications(self, state: ScanState) -> bool:
        """Determine if notifications should be skipped"""
        dry_run = state.meta.get('dry_run', False)
        has_events = len(state.policy_events) > 0
        
        return dry_run or not has_events
    
    def get_workflow_status(self) -> dict:
        """Get workflow configuration status"""
        node_timeouts = {
            "scan_plan": 60,
            "scan_git": 300,
            "scan_hf": 180,
            "normalize": 240,
            "embed_index": 600,
            "generate_bom": 120,
            "diff_previous": 120,
            "check_policies": 180,
            "notify": 120
        }
        
        if self.runtime_enabled:
            node_timeouts["runtime_collect"] = 120
        
        return {
            "dry_run": self.dry_run,
            "allowed_tools": list(self.allowed_tools),
            "runtime_enabled": self.runtime_enabled,
            "runtime_duration": self.runtime_duration,
            "node_timeouts": node_timeouts
        }

# Global workflow instance
ml_bom_workflow = MLBOMWorkflow()