from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import time
from core.schemas.models import Project, ScanState
from core.graph.workflow import ml_bom_workflow
from core.db.connection import db_manager
from core.bom.generator import BOMGenerator
from core.diff.engine import DiffEngine
from core.policy.engine import PolicyEngine
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-BOM Autopilot",
    description="Auto-discover ML artifacts and generate CycloneDX ML-BOM with policy checking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ProjectCreate(BaseModel):
    name: str
    repo_url: str
    default_branch: str = "main"

class ScanRequest(BaseModel):
    project: str
    dry_run: bool = False

class RuntimeScanRequest(BaseModel):
    project: str
    duration: int = 30
    dry_run: bool = False

class HealthResponse(BaseModel):
    status: str
    database: dict
    capabilities: dict

# Dependency to get database session
def get_db_session():
    return db_manager.get_session()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_health = db_manager.health_check()
    
    return HealthResponse(
        status="healthy" if db_health["status"] == "healthy" else "unhealthy",
        database=db_health,
        capabilities=db_manager.capabilities
    )

@app.get("/workflow/status")
async def get_workflow_status():
    """Get workflow configuration and status"""
    return ml_bom_workflow.get_workflow_status()

@app.get("/projects", response_model=List[Project])
async def list_projects():
    """List all projects"""
    with db_manager.get_session() as session:
        result = session.execute(text("SELECT id, name, repo_url, default_branch FROM projects"))
        projects = []
        for row in result:
            projects.append(Project(
                id=row.id,
                name=row.name,
                repo_url=row.repo_url,
                default_branch=row.default_branch
            ))
        return projects

@app.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    with db_manager.get_session() as session:
        try:
            result = session.execute(text("""
                INSERT INTO projects (name, repo_url, default_branch)
                VALUES (:name, :repo_url, :default_branch)
            """), {
                'name': project.name,
                'repo_url': project.repo_url,
                'default_branch': project.default_branch
            })
            session.commit()
            
            project_id = result.lastrowid
            return Project(
                id=project_id,
                name=project.name,
                repo_url=project.repo_url,
                default_branch=project.default_branch
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=400, detail=f"Failed to create project: {str(e)}")

@app.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: int):
    """Get project by ID"""
    with db_manager.get_session() as session:
        result = session.execute(text("""
            SELECT id, name, repo_url, default_branch 
            FROM projects 
            WHERE id = :project_id
        """), {'project_id': project_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return Project(
            id=result.id,
            name=result.name,
            repo_url=result.repo_url,
            default_branch=result.default_branch
        )

@app.post("/scan")
async def run_scan(request: ScanRequest):
    """Run ML-BOM scan for a project"""
    # Get project by name
    with db_manager.get_session() as session:
        result = session.execute(text("""
            SELECT id, name, repo_url, default_branch 
            FROM projects 
            WHERE name = :project_name
        """), {'project_name': request.project}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Project '{request.project}' not found")
        
        project = Project(
            id=result.id,
            name=result.name,
            repo_url=result.repo_url,
            default_branch=result.default_branch
        )
    
    # Run scan
    try:
        raw_scan_result = ml_bom_workflow.run_scan(project, dry_run=request.dry_run)
        
        # Debug the scan_result structure
        logger.info(f"scan_result type: {type(raw_scan_result)}")
        logger.info(f"scan_result attributes: {dir(raw_scan_result)}")
        
        # Convert the AddableValuesDict to a proper ScanState object
        from core.schemas.models import ScanState
        
        # Initialize a new ScanState with default values
        scan_result = ScanState(
            project=project,
            models=[],
            datasets=[],
            prompts=[],
            tools=[],
            evidence_chunks=[],
            policy_events=[],
            actions=[],
            error=None
        )
        
        # Copy attributes from raw_scan_result to scan_result
        if hasattr(raw_scan_result, 'get'):
            # Copy data from raw result to scan_result
            for key in raw_scan_result.keys():
                if hasattr(scan_result, key):
                    setattr(scan_result, key, raw_scan_result.get(key))
            
            # Set meta dictionary
            scan_result.meta = raw_scan_result.get('meta', {})
        
        # Calculate scan duration
        if hasattr(scan_result, 'meta') and isinstance(scan_result.meta, dict):
            scan_start = scan_result.meta.get('scan_start_time', 0)
        else:
            logger.warning("scan_result does not have meta attribute or meta is not a dict")
            scan_result.meta = {}
            scan_start = 0
            
        scan_duration = time.time() - scan_start if scan_start else 0
        
        # Return scan summary including final state
        return {
            "project_id": project.id,
            "project_name": project.name,
            "dry_run": request.dry_run,
            "scan_duration_seconds": round(scan_duration, 2),
            "commit_sha": scan_result.commit_sha if hasattr(scan_result, 'commit_sha') else None,
            "components": {
                "models": len(scan_result.models) if hasattr(scan_result, 'models') else 0,
                "datasets": len(scan_result.datasets) if hasattr(scan_result, 'datasets') else 0,
                "prompts": len(scan_result.prompts) if hasattr(scan_result, 'prompts') else 0,
                "tools": len(scan_result.tools) if hasattr(scan_result, 'tools') else 0,
                "evidence_chunks": len(scan_result.evidence_chunks) if hasattr(scan_result, 'evidence_chunks') else 0
            },
            "bom_id": scan_result.bom.id if hasattr(scan_result, 'bom') and scan_result.bom else None,
            "bom_sha256": scan_result.meta.get('bom_sha256') if hasattr(scan_result, 'meta') else None,
            "diff_summary": scan_result.diff.summary if hasattr(scan_result, 'diff') and scan_result.diff else None,
            "policy_events": [
                {
                    "id": event.id,
                    "severity": event.severity.value,
                    "rule": event.rule,
                    "artifact": event.artifact,
                    "details": event.details
                }
                for event in scan_result.policy_events if hasattr(scan_result, 'policy_events')
            ],
            "action_ids": [action.id for action in scan_result.actions if hasattr(scan_result, 'actions') and action.id],
            "counters": scan_result.meta.get('counters', {}) if hasattr(scan_result, 'meta') else {},
            "error": scan_result.error if hasattr(scan_result, 'error') else None
        }
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.get("/projects/{project_id}/boms")
async def get_project_boms(project_id: int, limit: int = 10):
    """Get BOMs for a project"""
    with db_manager.get_session() as session:
        result = session.execute(text("""
            SELECT id, bom_json, created_at
            FROM boms
            WHERE project_id = :project_id
            ORDER BY created_at DESC
            LIMIT :limit
        """), {'project_id': project_id, 'limit': limit})
        
        boms = []
        for row in result:
            boms.append({
                'id': row.id,
                'created_at': row.created_at.isoformat(),
                'component_count': len(json.loads(row.bom_json).get('components', []))
            })
        
        return boms

@app.get("/boms/{bom_id}")
async def get_bom(bom_id: int):
    """Get BOM by ID"""
    with db_manager.get_session() as session:
        result = session.execute(text("""
            SELECT id, project_id, bom_json, created_at
            FROM boms
            WHERE id = :bom_id
        """), {'bom_id': bom_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="BOM not found")
        
        return {
            'id': result.id,
            'project_id': result.project_id,
            'bom': json.loads(result.bom_json),
            'created_at': result.created_at.isoformat()
        }

@app.get("/projects/{project_id}/diffs")
async def get_project_diffs(project_id: int, limit: int = 10):
    """Get diffs for a project"""
    diff_engine = DiffEngine()
    diffs = diff_engine.get_project_diffs(project_id, limit)
    
    return [
        {
            'id': diff.id,
            'from_bom': diff.from_bom,
            'to_bom': diff.to_bom,
            'summary': diff.summary,
            'created_at': diff.created_at.isoformat()
        }
        for diff in diffs
    ]

@app.get("/projects/{project_id}/policy-events")
async def get_project_policy_events(project_id: int, limit: int = 50):
    """Get policy events for a project"""
    policy_engine = PolicyEngine()
    events = policy_engine.get_project_events(project_id, limit)
    
    return [
        {
            'id': event.id,
            'severity': event.severity.value,
            'rule': event.rule,
            'artifact': event.artifact,
            'details': event.details,
            'created_at': event.created_at.isoformat()
        }
        for event in events
    ]

@app.get("/projects/{project_id}/actions")
async def get_project_actions(project_id: int, limit: int = 20):
    """Get actions for a project"""
    with db_manager.get_session() as session:
        result = session.execute(text("""
            SELECT id, kind, payload, response, status, created_at
            FROM actions
            WHERE project_id = :project_id
            ORDER BY created_at DESC
            LIMIT :limit
        """), {'project_id': project_id, 'limit': limit})
        
        actions = []
        for row in result:
            actions.append({
                'id': row.id,
                'kind': row.kind,
                'payload': json.loads(row.payload) if row.payload else {},
                'response': json.loads(row.response) if row.response else {},
                'status': row.status,
                'created_at': row.created_at.isoformat()
            })
        
        return actions

@app.get("/search/{project_id}")
async def search_evidence(project_id: int, query: str, limit: int = 10):
    """Search evidence chunks"""
    from core.embeddings.embedder import EmbeddingService
    
    embedder = EmbeddingService()
    results = embedder.search_similar(project_id, query, limit)
    
    return results

@app.post("/projects/{project_id}/policy-events/{event_id}/notify/slack")
async def send_slack_notification(project_id: int, event_id: int):
    """Send Slack notification for a policy event"""
    try:
        from core.mcp_tools.slack import SlackNotifier
        
        # Get the policy event
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT pe.*, p.name as project_name
                FROM policy_events pe
                JOIN projects p ON pe.project_id = p.id
                WHERE pe.id = :event_id AND pe.project_id = :project_id
            """), {'event_id': event_id, 'project_id': project_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Policy event not found")
            
            # Create notification
            slack_notifier = SlackNotifier()
            response = slack_notifier.send_policy_alert({
                'id': result.id,
                'severity': result.severity,
                'rule': result.rule,
                'artifact': json.loads(result.artifact) if result.artifact else {},
                'details': json.loads(result.details) if result.details else {},
                'project_name': result.project_name
            })
            
            # Log the action
            session.execute(text("""
                INSERT INTO actions (project_id, kind, payload, response, status)
                VALUES (:project_id, 'slack', :payload, :response, :status)
            """), {
                'project_id': project_id,
                'kind': 'slack',
                'payload': json.dumps({'event_id': event_id}),
                'response': json.dumps(response),
                'status': 'ok' if response.get('ok') else 'fail'
            })
            session.commit()
            
            return {"status": "success", "response": response}
            
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")

@app.post("/projects/{project_id}/policy-events/{event_id}/notify/jira")
async def create_jira_ticket(project_id: int, event_id: int):
    """Create Jira ticket for a policy event"""
    try:
        from core.mcp_tools.jira import JiraTicketCreator
        
        # Get the policy event
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT pe.*, p.name as project_name
                FROM policy_events pe
                JOIN projects p ON pe.project_id = p.id
                WHERE pe.id = :event_id AND pe.project_id = :project_id
            """), {'event_id': event_id, 'project_id': project_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Policy event not found")
            
            # Create Jira ticket
            jira_creator = JiraTicketCreator()
            response = jira_creator.create_policy_ticket({
                'id': result.id,
                'severity': result.severity,
                'rule': result.rule,
                'artifact': json.loads(result.artifact) if result.artifact else {},
                'details': json.loads(result.details) if result.details else {},
                'project_name': result.project_name
            })
            
            # Log the action
            session.execute(text("""
                INSERT INTO actions (project_id, kind, payload, response, status)
                VALUES (:project_id, 'jira', :payload, :response, :status)
            """), {
                'project_id': project_id,
                'kind': 'jira',
                'payload': json.dumps({'event_id': event_id}),
                'response': json.dumps(response),
                'status': 'ok' if response.get('id') else 'fail'
            })
            session.commit()
            
            return {"status": "success", "response": response}
            
    except Exception as e:
        logger.error(f"Failed to create Jira ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")

# Runtime tracing endpoints
@app.get("/projects/{project_id}/runtime/events")
async def get_runtime_events(project_id: int, limit: int = 100):
    """Get runtime events for a project"""
    from core.runtime.collector import RuntimeCollector
    
    collector = RuntimeCollector(project_id)
    events = collector.get_runtime_events(limit)
    
    return {
        "project_id": project_id,
        "events": events,
        "total": len(events)
    }

@app.get("/projects/{project_id}/runtime/summary")
async def get_runtime_summary(project_id: int):
    """Get runtime collection summary for a project"""
    from core.runtime.collector import RuntimeIntegration
    
    summary = RuntimeIntegration.get_runtime_summary(project_id)
    
    return {
        "project_id": project_id,
        "summary": summary
    }

@app.delete("/projects/{project_id}/runtime/events")
async def clear_runtime_events(project_id: int):
    """Clear runtime events for a project"""
    from core.runtime.collector import RuntimeCollector
    
    try:
        collector = RuntimeCollector(project_id)
        collector.clear_runtime_events()
        
        return {"status": "success", "message": f"Cleared runtime events for project {project_id}"}
        
    except Exception as e:
        logger.error(f"Failed to clear runtime events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear events: {str(e)}")

@app.post("/scan/runtime")
async def run_runtime_scan(request: RuntimeScanRequest):
    """Run runtime-only scan for a project"""
    from core.runtime.collector import RuntimeCollector
    
    # Get project by name
    with db_manager.get_session() as session:
        result = session.execute(text("""
            SELECT id, name, repo_url, default_branch 
            FROM projects 
            WHERE name = :project_name
        """), {'project_name': request.project}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Project '{request.project}' not found")
    
    try:
        collector = RuntimeCollector(result.id)
        
        if request.dry_run:
            return {
                "project_id": result.id,
                "project_name": request.project,
                "dry_run": True,
                "message": "DRY_RUN mode: Runtime collection would run for {} seconds".format(request.duration),
                "artifacts": []
            }
        
        # Run runtime collection
        artifacts = collector.collect_for_duration(request.duration)
        summary = collector.get_collection_summary()
        
        return {
            "project_id": result.id,
            "project_name": request.project,
            "duration_seconds": request.duration,
            "artifacts_discovered": len(artifacts),
            "artifacts": [
                {
                    "id": artifact.id,
                    "kind": artifact.kind,
                    "name": artifact.name,
                    "version": artifact.version,
                    "provider": artifact.provider,
                    "file_path": artifact.file_path,
                    "runtime_detected": artifact.metadata.get('runtime_detected', False) if artifact.metadata else False
                }
                for artifact in artifacts
            ],
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Runtime scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Runtime scan failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)