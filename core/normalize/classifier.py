import re
import hashlib
import subprocess
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from core.schemas.models import Model, Dataset, Prompt, Tool, ScanState, ToolType
from core.scan_hf.fetcher import HFCard
import logging
from .ml_detector import detect_frameworks_in_file, get_detected_ml_info

logger = logging.getLogger(__name__)

class ArtifactClassifier:
    """Classifies and normalizes ML artifacts with SPDX license detection"""
    
    def _extract_models_from_file(self, project_id: int, file_path: str, full_path: Path, commit_sha: str) -> List[Model]:
        """Extract ML models from a Python file using enhanced detection"""
        models = []
        
        try:
            # Use the ML detector to identify frameworks and model types
            detected = detect_frameworks_in_file(full_path)
            ml_info = get_detected_ml_info(detected)
            
            # Only continue if we detected something
            if not ml_info['frameworks'] and not ml_info['models']:
                return models
                
            # Try to detect license in the file
            license, is_unknown = self._normalize_license_enhanced(None, full_path)
            
            # Generate model name based on file path and detected frameworks
            base_name = Path(file_path).stem
            
            # Create canonical ID for model
            model_id = hashlib.md5(f"{project_id}:{file_path}".encode('utf-8')).hexdigest()
            
            # Create metadata for the model
            meta = {
                'file_path': file_path,
                'detected_frameworks': ml_info['frameworks'],
                'model_architectures': ml_info['models'],
                'canonical_id': model_id
            }
            
            if is_unknown:
                meta['license_warning'] = f"Unknown or unrecognized license: {license}"
                
            # Create a model for each detected framework
            for framework in ml_info['frameworks']:
                model_name = f"{base_name}_{framework}"
                
                model = Model(
                    project_id=project_id,
                    name=model_name,
                    provider=framework,
                    version="unknown",
                    license=license,
                    repo_path=file_path,
                    commit_sha=commit_sha,
                    meta=meta
                )
                models.append(model)
                
            # If no frameworks detected but model types are detected, create a generic model
            if not models and ml_info['models']:
                model_type = ml_info['models'][0]
                model_name = f"{base_name}_{model_type}"
                
                model = Model(
                    project_id=project_id,
                    name=model_name,
                    provider="custom",
                    version="unknown",
                    license=license,
                    repo_path=file_path,
                    commit_sha=commit_sha,
                    meta=meta
                )
                models.append(model)
                
            return models
            
        except Exception as e:
            logger.warning(f"Failed to extract models from {file_path}: {e}")
            return models
    
    def __init__(self):
        self.spdx_license_map = {
            'mit': 'MIT',
            'apache-2.0': 'Apache-2.0',
            'apache': 'Apache-2.0',
            'bsd-3-clause': 'BSD-3-Clause',
            'bsd': 'BSD-3-Clause',
            'gpl-3.0': 'GPL-3.0',
            'gpl': 'GPL-3.0',
            'cc-by-4.0': 'CC-BY-4.0',
            'cc-by-sa-4.0': 'CC-BY-SA-4.0',
            'openrail': 'OpenRAIL',
            'bigscience-openrail-m': 'OpenRAIL-M',
            'creativeml-openrail-m': 'OpenRAIL-M'
        }
        
        # Custom/proprietary licenses that should be flagged as unknown
        self.unknown_license_patterns = [
            'llama2', 'llama', 'custom', 'proprietary', 'internal', 'restricted'
        ]
        
        self.model_providers = {
            'openai': ['gpt', 'text-embedding', 'whisper', 'dall-e'],
            'anthropic': ['claude'],
            'meta': ['llama', 'opt'],
            'google': ['bert', 'flan', 't5', 'palm'],
            'microsoft': ['dialoGPT', 'unilm'],
            'huggingface': ['transformers']
        }
        
        # Enhanced SPDX license identifiers
        self.known_spdx_licenses = {
            'MIT', 'Apache-2.0', 'GPL-3.0', 'GPL-2.0', 'BSD-3-Clause', 'BSD-2-Clause',
            'CC-BY-4.0', 'CC-BY-SA-4.0', 'OpenRAIL', 'OpenRAIL-M', 'LGPL-3.0', 'LGPL-2.1',
            'MPL-2.0', 'ISC', 'Unlicense', 'CC0-1.0'
        }
    

    
    def _generate_canonical_id(self, project_name: str, name: str, kind: str, 
                              provider: str, version: str) -> str:
        """Generate stable, canonical ID for artifact"""
        # Format: project:name:kind:provider:version
        # Normalize components to ensure stability - replace all non-alphanumeric with underscore
        normalized_project = re.sub(r'[^a-zA-Z0-9]', '_', project_name.lower())
        normalized_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        normalized_kind = kind.lower()
        normalized_provider = re.sub(r'[^a-zA-Z0-9]', '_', provider.lower())
        normalized_version = re.sub(r'[^a-zA-Z0-9\.]', '_', version)
        
        return f"{normalized_project}:{normalized_name}:{normalized_kind}:{normalized_provider}:{normalized_version}"
    
    def _detect_license_in_file(self, file_path: Path) -> Optional[str]:
        """Detect license in file content using pattern matching"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Common license patterns
            license_patterns = [
                (r'SPDX-License-Identifier:\s*([A-Za-z0-9\.\-\+]+)', 'spdx'),
                (r'License:\s*([A-Za-z0-9\.\-\+\s]+)', 'license_field'),
                (r'MIT License', 'MIT'),
                (r'Apache License.*Version 2\.0', 'Apache-2.0'),
                (r'GNU General Public License.*version 3', 'GPL-3.0'),
                (r'BSD.*3.*Clause', 'BSD-3-Clause'),
                (r'Creative Commons.*Attribution.*4\.0', 'CC-BY-4.0'),
                (r'OpenRAIL', 'OpenRAIL'),
            ]
            
            for pattern, license_id in license_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    if license_id in ['spdx', 'license_field']:
                        return match.group(1).strip()
                    else:
                        return license_id
            
        except Exception as e:
            logger.debug(f"Failed to read file {file_path} for license detection: {e}")
        
        return None
    
    def _normalize_license_enhanced(self, license_str: Optional[str], file_path: Optional[Path] = None) -> Tuple[Optional[str], bool]:
        """Enhanced license normalization with unknown license flagging"""
        if not license_str:
            # Try file-based detection if we have a file path
            if file_path:
                detected_license = self._detect_license_in_file(file_path)
                if detected_license:
                    # Recursively normalize the detected license
                    return self._normalize_license_enhanced(detected_license, None)
            return None, True  # Unknown license
        
        license_lower = license_str.lower().strip()
        
        # Check for known unknown/proprietary licenses first
        for unknown_pattern in self.unknown_license_patterns:
            if unknown_pattern in license_lower:
                logger.warning(f"Unknown/proprietary license detected: {license_str}")
                return license_str, True
        
        # Direct SPDX mapping
        if license_lower in self.spdx_license_map:
            return self.spdx_license_map[license_lower], False
        
        # Fuzzy matching for known licenses
        for key, spdx in self.spdx_license_map.items():
            if key in license_lower:
                return spdx, False
        
        # Check if it's in our known SPDX licenses set
        if license_str in self.known_spdx_licenses:
            return license_str, False
        
        # Check if it looks like a valid SPDX identifier (basic pattern)
        if re.match(r'^[A-Za-z0-9\.\-\+]+$', license_str) and len(license_str) <= 50:
            # Could be a valid SPDX license we don't know about
            return license_str, False
        
        # Unknown license
        logger.warning(f"Unknown license detected: {license_str}")
        return license_str, True  # Return original but flag as unknown

    def normalize_artifacts(self, state: ScanState, hf_cards: Dict[str, HFCard]) -> ScanState:
        """Normalize and classify all artifacts"""
        try:
            # Process HuggingFace cards
            for slug, card in hf_cards.items():
                if card.type == 'model':
                    model = self._create_model_from_hf(state.project.id, slug, card, state.commit_sha)
                    if model:
                        state.models.append(model)
                elif card.type == 'dataset':
                    dataset = self._create_dataset_from_hf(state.project.id, slug, card, state.commit_sha)
                    if dataset:
                        state.datasets.append(dataset)
            
            # Process files for prompts and tools
            repo_path = f"repos/id={state.project.id}_{state.project.name.replace(' ', '_')}"
            
            # Convert file_candidates to files list for processing
            if hasattr(state, 'file_candidates') and state.file_candidates:
                file_paths = [candidate.file_path for candidate in state.file_candidates]
                # Get commit_sha from first candidate if not set
                if not state.commit_sha and state.file_candidates:
                    state.commit_sha = state.file_candidates[0].commit_sha
            else:
                file_paths = getattr(state, 'files', [])
            
            for file_path in file_paths:
                full_path = Path(repo_path) / file_path
                
                # Extract ML models from Python files
                if file_path.endswith('.py'):
                    models = self._extract_models_from_file(state.project.id, file_path, full_path, state.commit_sha)
                    state.models.extend(models)
                
                if self._is_prompt_file(file_path):
                    prompts = self._extract_prompts_from_file(state.project.id, file_path, full_path, state.commit_sha)
                    state.prompts.extend(prompts)
                
                if self._is_tool_file(file_path):
                    tools = self._extract_tools_from_file(state.project.id, file_path, full_path, state.commit_sha)
                    state.tools.extend(tools)
            
            logger.info(f"Normalized {len(state.models)} models, {len(state.datasets)} datasets, "
                       f"{len(state.prompts)} prompts, {len(state.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to normalize artifacts: {e}")
            state.error = str(e)
        
        return state
    
    def _create_model_from_hf(self, project_id: int, slug: str, card: HFCard, commit_sha: str) -> Optional[Model]:
        """Create Model from HuggingFace card with enhanced license detection"""
        try:
            provider = self._detect_provider(slug, card)
            version = self._extract_version(slug, card)
            license, is_unknown = self._normalize_license_enhanced(card.license)
            
            # Generate canonical ID
            project_name = f"project_{project_id}"  # We'll need to get actual project name
            canonical_id = self._generate_canonical_id(project_name, slug.split('/')[-1], 
                                                     'model', provider, version)
            
            meta = {
                'hf_slug': slug,
                'model_type': card.model_type,
                'pipeline_tag': card.pipeline_tag,
                'library_name': card.library_name,
                'tags': card.tags,
                'canonical_id': canonical_id,
                'license_unknown': is_unknown
            }
            
            if is_unknown:
                meta['license_warning'] = f"Unknown or unrecognized license: {license}"
            
            return Model(
                project_id=project_id,
                name=slug.split('/')[-1],
                provider=provider,
                version=version,
                license=license,
                source_url=f"https://huggingface.co/{slug}",
                commit_sha=commit_sha,
                meta=meta
            )
        except Exception as e:
            logger.warning(f"Failed to create model from {slug}: {e}")
            return None
    
    def _create_dataset_from_hf(self, project_id: int, slug: str, card: HFCard, commit_sha: str) -> Optional[Dataset]:
        """Create Dataset from HuggingFace card with enhanced license detection"""
        try:
            version = self._extract_version(slug, card)
            license, is_unknown = self._normalize_license_enhanced(card.license)
            
            # Generate canonical ID
            project_name = f"project_{project_id}"  # We'll need to get actual project name
            canonical_id = self._generate_canonical_id(project_name, slug.split('/')[-1], 
                                                     'dataset', 'huggingface', version)
            
            meta = {
                'hf_slug': slug,
                'tags': card.tags,
                'canonical_id': canonical_id,
                'license_unknown': is_unknown
            }
            
            if is_unknown:
                meta['license_warning'] = f"Unknown or unrecognized license: {license}"
            
            return Dataset(
                project_id=project_id,
                name=slug.split('/')[-1],
                version=version,
                license=license,
                source_url=f"https://huggingface.co/datasets/{slug}",
                commit_sha=commit_sha,
                meta=meta
            )
        except Exception as e:
            logger.warning(f"Failed to create dataset from {slug}: {e}")
            return None
    
    def _is_prompt_file(self, file_path: str) -> bool:
        """Check if file contains prompts"""
        return (
            file_path.endswith('.prompt') or
            '/prompts/' in file_path or
            'prompt' in file_path.lower()
        )
    
    def _is_tool_file(self, file_path: str) -> bool:
        """Check if file defines tools"""
        return (
            file_path.endswith('.py') or
            file_path.endswith('.json') or
            'tools' in file_path.lower() or
            'mcp' in file_path.lower()
        )
    
    def _extract_prompts_from_file(self, project_id: int, file_path: str, full_path: Path, commit_sha: str) -> List[Prompt]:
        """Extract prompts from a file with enhanced classification"""
        prompts = []
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Enhanced prompt extraction patterns
            prompt_patterns = [
                (r'"""([^"]{50,})"""', 'triple_quote_double'),  # Triple quoted strings
                (r"'''([^']{50,})'''", 'triple_quote_single'),  # Triple quoted strings
                (r'prompt\s*=\s*["\']([^"\']{50,})["\']', 'variable_prompt'),  # Variable assignments
                (r'template\s*=\s*["\']([^"\']{50,})["\']', 'variable_template'),
                (r'system_prompt\s*=\s*["\']([^"\']{50,})["\']', 'system_prompt'),
                (r'user_prompt\s*=\s*["\']([^"\']{50,})["\']', 'user_prompt'),
                (r'PROMPT\s*=\s*["\']([^"\']{50,})["\']', 'constant_prompt')
            ]
            
            # Try to detect license in the file
            license, is_unknown = self._normalize_license_enhanced(None, full_path)
            
            project_name = f"project_{project_id}"  # We'll need to get actual project name
            
            for i, (pattern, pattern_name) in enumerate(prompt_patterns):
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                for j, match in enumerate(matches):
                    prompt_content = match.strip()
                    if len(prompt_content) > 50:  # Minimum length for a prompt
                        blob_sha = hashlib.sha256(prompt_content.encode()).hexdigest()
                        prompt_name = f"{Path(file_path).stem}_prompt_{i}_{j}"
                        
                        # Generate canonical ID
                        canonical_id = self._generate_canonical_id(project_name, prompt_name, 
                                                                 'prompt', 'local', '1.0')
                        
                        meta = {
                            'pattern_type': pattern_name,
                            'length': len(prompt_content),
                            'canonical_id': canonical_id,
                            'file_license': license,
                            'license_unknown': is_unknown
                        }
                        
                        if is_unknown and license:
                            meta['license_warning'] = f"Unknown license in file: {license}"
                        
                        prompt = Prompt(
                            project_id=project_id,
                            name=prompt_name,
                            version="1.0",
                            path=file_path,
                            commit_sha=commit_sha,
                            blob_sha=blob_sha,
                            meta=meta
                        )
                        prompts.append(prompt)
        
        except Exception as e:
            logger.warning(f"Failed to extract prompts from {file_path}: {e}")
        
        return prompts
    
    def _extract_tools_from_file(self, project_id: int, file_path: str, full_path: Path, commit_sha: str) -> List[Tool]:
        """Extract tool definitions from a file with enhanced classification"""
        tools = []
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Try to detect license in the file
            license, is_unknown = self._normalize_license_enhanced(None, full_path)
            project_name = f"project_{project_id}"  # We'll need to get actual project name
            
            # Look for API/tool definitions
            if file_path.endswith('.py'):
                # Enhanced Python function detection
                patterns = [
                    (r'def\s+(\w*(?:api|tool|function|call|handler|endpoint)\w*)\s*\([^)]*\):', 'function'),
                    (r'class\s+(\w*(?:API|Tool|Client|Service)\w*)\s*[:\(]', 'class'),
                    (r'@app\.(?:get|post|put|delete|patch)\s*\([^)]*\)\s*\ndef\s+(\w+)', 'fastapi_endpoint')
                ]
                
                for pattern, tool_type in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for tool_name in matches:
                        if tool_name and len(tool_name) > 2:  # Valid tool name
                            canonical_id = self._generate_canonical_id(project_name, tool_name, 
                                                                     'tool', 'local', '1.0')
                            
                            meta = {
                                'commit_sha': commit_sha,
                                'file': file_path,
                                'tool_type': tool_type,
                                'canonical_id': canonical_id,
                                'file_license': license,
                                'license_unknown': is_unknown
                            }
                            
                            if is_unknown and license:
                                meta['license_warning'] = f"Unknown license in file: {license}"
                            
                            tool = Tool(
                                project_id=project_id,
                                name=tool_name,
                                version="1.0",
                                type=ToolType.LIB,
                                spec={'language': 'python', 'file': file_path, 'type': tool_type},
                                meta=meta
                            )
                            tools.append(tool)
            
            elif file_path.endswith('.json'):
                # Enhanced JSON tool definitions (e.g., MCP tools, OpenAPI specs)
                try:
                    import json
                    data = json.loads(content)
                    
                    # MCP tool definitions
                    if isinstance(data, dict) and 'tools' in data:
                        for tool_name, tool_spec in data['tools'].items():
                            canonical_id = self._generate_canonical_id(project_name, tool_name, 
                                                                     'tool', 'mcp', 
                                                                     tool_spec.get('version', '1.0'))
                            
                            meta = {
                                'commit_sha': commit_sha, 
                                'file': file_path,
                                'canonical_id': canonical_id,
                                'file_license': license,
                                'license_unknown': is_unknown
                            }
                            
                            if is_unknown and license:
                                meta['license_warning'] = f"Unknown license in file: {license}"
                            
                            tool = Tool(
                                project_id=project_id,
                                name=tool_name,
                                version=tool_spec.get('version', '1.0'),
                                type=ToolType.MCP,
                                spec=tool_spec,
                                meta=meta
                            )
                            tools.append(tool)
                    
                    # OpenAPI/Swagger definitions
                    elif isinstance(data, dict) and ('openapi' in data or 'swagger' in data):
                        api_name = data.get('info', {}).get('title', Path(file_path).stem)
                        api_version = data.get('info', {}).get('version', '1.0')
                        
                        canonical_id = self._generate_canonical_id(project_name, api_name, 
                                                                 'tool', 'openapi', api_version)
                        
                        meta = {
                            'commit_sha': commit_sha,
                            'file': file_path,
                            'api_type': 'openapi',
                            'canonical_id': canonical_id,
                            'file_license': license,
                            'license_unknown': is_unknown
                        }
                        
                        if is_unknown and license:
                            meta['license_warning'] = f"Unknown license in file: {license}"
                        
                        tool = Tool(
                            project_id=project_id,
                            name=api_name,
                            version=api_version,
                            type=ToolType.API,
                            spec=data,
                            meta=meta
                        )
                        tools.append(tool)
                        
                except json.JSONDecodeError:
                    logger.debug(f"Invalid JSON in {file_path}, skipping tool extraction")
        
        except Exception as e:
            logger.warning(f"Failed to extract tools from {file_path}: {e}")
        
        return tools
    
    def _detect_provider(self, slug: str, card: HFCard) -> str:
        """Detect model provider"""
        slug_lower = slug.lower()
        
        for provider, keywords in self.model_providers.items():
            if any(keyword in slug_lower for keyword in keywords):
                return provider
        
        # Use organization name from slug
        if '/' in slug:
            return slug.split('/')[0]
        
        return 'unknown'
    
    def _extract_version(self, slug: str, card: HFCard) -> str:
        """Extract version from model/dataset"""
        # Look for version in slug
        version_match = re.search(r'v?(\d+\.?\d*\.?\d*)', slug)
        if version_match:
            return version_match.group(1)
        
        # Look for version in tags
        if card.tags:
            for tag in card.tags:
                if tag.startswith('v') and re.match(r'v\d+', tag):
                    return tag[1:]
        
        return "1.0"
    
