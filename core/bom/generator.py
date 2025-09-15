import json
import hashlib
import subprocess
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType, ComponentScope
from cyclonedx.output.json import JsonV1Dot5
from core.schemas.models import ScanState, BOM
from core.db.connection import db_manager
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class BOMGenerator:
    """Generates CycloneDX ML-BOM from scan results"""
    
    def __init__(self):
        pass
    
    def generate_bom(self, state: ScanState) -> ScanState:
        """Generate CycloneDX ML-BOM from scan state"""
        try:
            # Create CycloneDX BOM
            bom = Bom()
            bom.metadata.timestamp = datetime.now(timezone.utc)
            
            # Add models as components
            for model in state.models:
                component = self._create_model_component(model)
                bom.components.add(component)
            
            # Add datasets as components
            for dataset in state.datasets:
                component = self._create_dataset_component(dataset)
                bom.components.add(component)
            
            # Add prompts as components
            for prompt in state.prompts:
                component = self._create_prompt_component(prompt)
                bom.components.add(component)
            
            # Add tools as components
            for tool in state.tools:
                component = self._create_tool_component(tool)
                bom.components.add(component)
            
            # Convert to JSON using v1.5 format (latest available)
            json_output = JsonV1Dot5(bom)
            bom_json = json.loads(json_output.output_as_string())
            
            # Calculate and log SHA256 hash of BOM JSON
            bom_json_str = json.dumps(bom_json, sort_keys=True)
            bom_hash = hashlib.sha256(bom_json_str.encode()).hexdigest()
            logger.info(f"Generated BOM SHA256: {bom_hash}")
            
            # Validate BOM against CycloneDX v1.5 schema
            validation_result = self.validate_bom_with_tool(bom_json)
            if validation_result['valid']:
                logger.info("BOM validation: PASS")
            else:
                logger.error(f"BOM validation: FAIL - {validation_result['error']}")
                state.error = f"BOM validation failed: {validation_result['error']}"
                return state
            
            # Store in database
            bom_record = self._store_bom(state.project.id, bom_json, bom_hash)
            state.bom = bom_record
            
            logger.info(f"Generated BOM with {len(bom.components)} components")
            
        except Exception as e:
            logger.error(f"Failed to generate BOM: {e}")
            state.error = str(e)
        
        return state
    
    def _create_model_component(self, model) -> Component:
        """Create CycloneDX component for a model"""
        component = Component(
            type=ComponentType.MACHINE_LEARNING_MODEL,
            name=model.name,
            version=model.version,
            scope=ComponentScope.REQUIRED
        )
        
        # Add properties
        if model.provider:
            component.properties.add(self._create_property("provider", model.provider))
        
        if model.license:
            component.properties.add(self._create_property("license", model.license))
        
        if model.source_url:
            component.properties.add(self._create_property("source_url", model.source_url))
        
        if model.repo_path:
            component.properties.add(self._create_property("repo_path", model.repo_path))
        
        if model.commit_sha:
            component.properties.add(self._create_property("commit_sha", model.commit_sha))
        
        # Add metadata
        for key, value in model.meta.items():
            component.properties.add(self._create_property(f"meta.{key}", str(value)))
        
        return component
    
    def _create_dataset_component(self, dataset) -> Component:
        """Create CycloneDX component for a dataset"""
        component = Component(
            type=ComponentType.DATA,
            name=dataset.name,
            version=dataset.version,
            scope=ComponentScope.REQUIRED
        )
        
        # Add properties
        if dataset.license:
            component.properties.add(self._create_property("license", dataset.license))
        
        if dataset.source_url:
            component.properties.add(self._create_property("source_url", dataset.source_url))
        
        if dataset.commit_sha:
            component.properties.add(self._create_property("commit_sha", dataset.commit_sha))
        
        # Add metadata
        for key, value in dataset.meta.items():
            component.properties.add(self._create_property(f"meta.{key}", str(value)))
        
        return component
    
    def _create_prompt_component(self, prompt) -> Component:
        """Create CycloneDX component for a prompt"""
        component = Component(
            type=ComponentType.FILE,
            name=prompt.name,
            version=prompt.version,
            scope=ComponentScope.REQUIRED
        )
        
        # Add properties
        component.properties.add(self._create_property("type", "prompt"))
        component.properties.add(self._create_property("path", prompt.path))
        
        if prompt.commit_sha:
            component.properties.add(self._create_property("commit_sha", prompt.commit_sha))
        
        if prompt.blob_sha:
            component.properties.add(self._create_property("blob_sha", prompt.blob_sha))
        
        # Add metadata
        for key, value in prompt.meta.items():
            component.properties.add(self._create_property(f"meta.{key}", str(value)))
        
        return component
    
    def _create_tool_component(self, tool) -> Component:
        """Create CycloneDX component for a tool"""
        component = Component(
            type=ComponentType.LIBRARY,
            name=tool.name,
            version=tool.version,
            scope=ComponentScope.REQUIRED
        )
        
        # Add properties
        component.properties.add(self._create_property("type", "tool"))
        component.properties.add(self._create_property("tool_type", tool.type.value))
        
        # Add spec as properties
        for key, value in tool.spec.items():
            component.properties.add(self._create_property(f"spec.{key}", str(value)))
        
        # Add metadata
        for key, value in tool.meta.items():
            component.properties.add(self._create_property(f"meta.{key}", str(value)))
        
        return component
    
    def _create_property(self, name: str, value: str):
        """Create a property for CycloneDX component"""
        from cyclonedx.model import Property
        return Property(name=name, value=value)
    
    def _store_bom(self, project_id: int, bom_json: Dict[str, Any], bom_hash: str) -> BOM:
        """Store BOM in database"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                INSERT INTO boms (project_id, bom_json, created_at)
                VALUES (:project_id, :bom_json, :created_at)
            """), {
                'project_id': project_id,
                'bom_json': json.dumps(bom_json),
                'created_at': datetime.now(timezone.utc)
            })
            
            session.commit()
            
            bom_id = result.lastrowid
            
            # Log the BOM hash for audit purposes
            logger.info(f"Stored BOM ID {bom_id} with SHA256: {bom_hash}")
            
            return BOM(
                id=bom_id,
                project_id=project_id,
                bom_json=bom_json,
                created_at=datetime.now(timezone.utc)
            )
    
    def get_latest_bom(self, project_id: int) -> BOM:
        """Get the latest BOM for a project"""
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, project_id, bom_json, created_at
                FROM boms
                WHERE project_id = :project_id
                ORDER BY created_at DESC
                LIMIT 1
            """), {'project_id': project_id}).fetchone()
            
            if result:
                return BOM(
                    id=result.id,
                    project_id=result.project_id,
                    bom_json=json.loads(result.bom_json),
                    created_at=result.created_at
                )
            
            return None
    
    def validate_bom(self, bom_json: Dict[str, Any]) -> bool:
        """Validate BOM against CycloneDX schema (basic validation)"""
        try:
            # Basic validation - check required fields
            required_fields = ['bomFormat', 'specVersion', 'version', 'metadata']
            
            for field in required_fields:
                if field not in bom_json:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Check components structure
            if 'components' in bom_json:
                for component in bom_json['components']:
                    if 'type' not in component or 'name' not in component:
                        logger.error("Component missing required fields")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"BOM validation failed: {e}")
            return False
    
    def validate_bom_with_tool(self, bom_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate BOM using cyclonedx-python-lib validate command"""
        try:
            # Write BOM to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(bom_json, temp_file, indent=2)
                temp_file_path = temp_file.name
            
            try:
                # Run cyclonedx-python-lib validate command
                result = subprocess.run([
                    'python', '-m', 'cyclonedx.validation.json',
                    temp_file_path
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    return {'valid': True, 'output': result.stdout}
                else:
                    return {
                        'valid': False, 
                        'error': result.stderr or result.stdout,
                        'returncode': result.returncode
                    }
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except subprocess.TimeoutExpired:
            logger.error("BOM validation timed out")
            return {'valid': False, 'error': 'Validation timeout'}
        except FileNotFoundError:
            logger.warning("cyclonedx-python-lib validation tool not found, falling back to basic validation")
            return {'valid': self.validate_bom(bom_json), 'error': 'Validation tool not available'}
        except Exception as e:
            logger.error(f"BOM validation with tool failed: {e}")
            return {'valid': False, 'error': str(e)}