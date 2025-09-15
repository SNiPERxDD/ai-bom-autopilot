import json
from typing import Dict, Any, List, Optional
from core.schemas.models import BOM, BOMDiff, ScanState
from core.db.connection import db_manager
from sqlalchemy import text
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class DiffEngine:
    """Compares BOMs and generates structured diffs"""
    
    def __init__(self):
        pass
    
    def generate_diff(self, state: ScanState) -> ScanState:
        """Generate diff between current and previous BOM"""
        try:
            if not state.bom:
                logger.warning("No current BOM to diff")
                return state
            
            # Get previous BOM
            previous_bom = self._get_previous_bom(state.project.id, state.bom.id)
            
            if not previous_bom:
                logger.info("No previous BOM found, this is the first scan")
                return state
            
            # Generate diff
            diff_summary = self._compare_boms(previous_bom.bom_json, state.bom.bom_json)
            
            # Store diff
            diff_record = self._store_diff(state.project.id, previous_bom.id, state.bom.id, diff_summary)
            state.diff = diff_record
            
            logger.info(f"Generated diff with {len(diff_summary.get('changes', []))} changes")
            
        except Exception as e:
            logger.error(f"Failed to generate diff: {e}")
            state.error = str(e)
        
        return state
    
    def _get_previous_bom(self, project_id: int, current_bom_id: int) -> Optional[BOM]:
        """Get the previous BOM for comparison"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, project_id, bom_json, created_at
                FROM boms
                WHERE project_id = :project_id AND id < :current_bom_id
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                'project_id': project_id,
                'current_bom_id': current_bom_id
            }).fetchone()
            
            if result:
                return BOM(
                    id=result.id,
                    project_id=result.project_id,
                    bom_json=json.loads(result.bom_json),
                    created_at=result.created_at
                )
            
            return None
    
    def _compare_boms(self, old_bom: Dict[str, Any], new_bom: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two BOMs and generate diff summary"""
        diff_summary = {
            'changes': [],
            'added_components': [],
            'removed_components': [],
            'modified_components': [],
            'stats': {
                'total_changes': 0,
                'additions': 0,
                'removals': 0,
                'modifications': 0
            }
        }
        
        # Get components from both BOMs
        old_components = {self._get_component_id(comp): comp 
                         for comp in old_bom.get('components', [])}
        new_components = {self._get_component_id(comp): comp 
                         for comp in new_bom.get('components', [])}
        
        # Find added components
        for comp_id, component in new_components.items():
            if comp_id not in old_components:
                diff_summary['added_components'].append({
                    'id': comp_id,
                    'name': component.get('name'),
                    'type': component.get('type'),
                    'version': component.get('version')
                })
                diff_summary['changes'].append({
                    'type': 'addition',
                    'component_id': comp_id,
                    'component_name': component.get('name'),
                    'details': f"Added {component.get('type')} component"
                })
        
        # Find removed components
        for comp_id, component in old_components.items():
            if comp_id not in new_components:
                diff_summary['removed_components'].append({
                    'id': comp_id,
                    'name': component.get('name'),
                    'type': component.get('type'),
                    'version': component.get('version')
                })
                diff_summary['changes'].append({
                    'type': 'removal',
                    'component_id': comp_id,
                    'component_name': component.get('name'),
                    'details': f"Removed {component.get('type')} component"
                })
        
        # Find modified components
        for comp_id in set(old_components.keys()) & set(new_components.keys()):
            old_comp = old_components[comp_id]
            new_comp = new_components[comp_id]
            
            modifications = self._compare_components(old_comp, new_comp)
            if modifications:
                diff_summary['modified_components'].append({
                    'id': comp_id,
                    'name': new_comp.get('name'),
                    'modifications': modifications
                })
                
                for mod in modifications:
                    diff_summary['changes'].append({
                        'type': 'modification',
                        'component_id': comp_id,
                        'component_name': new_comp.get('name'),
                        'field': mod['field'],
                        'old_value': mod['old_value'],
                        'new_value': mod['new_value'],
                        'details': f"Changed {mod['field']} from '{mod['old_value']}' to '{mod['new_value']}'"
                    })
        
        # Update stats
        diff_summary['stats']['additions'] = len(diff_summary['added_components'])
        diff_summary['stats']['removals'] = len(diff_summary['removed_components'])
        diff_summary['stats']['modifications'] = len(diff_summary['modified_components'])
        diff_summary['stats']['total_changes'] = len(diff_summary['changes'])
        
        return diff_summary
    
    def _get_component_id(self, component: Dict[str, Any]) -> str:
        """Generate stable component ID"""
        name = component.get('name', '')
        comp_type = component.get('type', '')
        
        # Look for provider in properties
        provider = ''
        for prop in component.get('properties', []):
            if prop.get('name') == 'provider':
                provider = prop.get('value', '')
                break
        
        return f"{name}:{comp_type}:{provider}"
    
    def _compare_components(self, old_comp: Dict[str, Any], new_comp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare two components and return modifications"""
        modifications = []
        
        # Compare basic fields
        fields_to_compare = ['version', 'scope']
        
        for field in fields_to_compare:
            old_value = old_comp.get(field)
            new_value = new_comp.get(field)
            
            if old_value != new_value:
                modifications.append({
                    'field': field,
                    'old_value': str(old_value) if old_value else None,
                    'new_value': str(new_value) if new_value else None
                })
        
        # Compare properties
        old_props = {prop.get('name'): prop.get('value') 
                    for prop in old_comp.get('properties', [])}
        new_props = {prop.get('name'): prop.get('value') 
                    for prop in new_comp.get('properties', [])}
        
        # Important properties to track
        important_props = ['license', 'source_url', 'commit_sha', 'blob_sha']
        
        for prop_name in important_props:
            old_value = old_props.get(prop_name)
            new_value = new_props.get(prop_name)
            
            if old_value != new_value:
                modifications.append({
                    'field': f'property.{prop_name}',
                    'old_value': old_value,
                    'new_value': new_value
                })
        
        return modifications
    
    def _store_diff(self, project_id: int, from_bom_id: int, to_bom_id: int, 
                   summary: Dict[str, Any]) -> BOMDiff:
        """Store diff in database"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                INSERT INTO bom_diffs (project_id, from_bom, to_bom, summary, created_at)
                VALUES (:project_id, :from_bom, :to_bom, :summary, :created_at)
            """), {
                'project_id': project_id,
                'from_bom': from_bom_id,
                'to_bom': to_bom_id,
                'summary': json.dumps(summary),
                'created_at': datetime.now(timezone.utc)
            })
            
            session.commit()
            
            diff_id = result.lastrowid
            
            return BOMDiff(
                id=diff_id,
                project_id=project_id,
                from_bom=from_bom_id,
                to_bom=to_bom_id,
                summary=summary,
                created_at=datetime.now(timezone.utc)
            )
    
    def get_diff_by_id(self, diff_id: int) -> Optional[BOMDiff]:
        """Get diff by ID"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, project_id, from_bom, to_bom, summary, created_at
                FROM bom_diffs
                WHERE id = :diff_id
            """), {'diff_id': diff_id}).fetchone()
            
            if result:
                return BOMDiff(
                    id=result.id,
                    project_id=result.project_id,
                    from_bom=result.from_bom,
                    to_bom=result.to_bom,
                    summary=json.loads(result.summary),
                    created_at=result.created_at
                )
            
            return None
    
    def get_project_diffs(self, project_id: int, limit: int = 10) -> List[BOMDiff]:
        """Get recent diffs for a project"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, project_id, from_bom, to_bom, summary, created_at
                FROM bom_diffs
                WHERE project_id = :project_id
                ORDER BY created_at DESC
                LIMIT :limit
            """), {
                'project_id': project_id,
                'limit': limit
            })
            
            diffs = []
            for row in result:
                diffs.append(BOMDiff(
                    id=row.id,
                    project_id=row.project_id,
                    from_bom=row.from_bom,
                    to_bom=row.to_bom,
                    summary=json.loads(row.summary),
                    created_at=row.created_at
                ))
            
            return diffs