"""
Runtime event normalizer for AI/ML artifacts.

This module normalizes runtime events captured by the tracer into
standardized AI artifacts that can be used for BOM generation.
"""

import hashlib
import json
import re
from typing import List, Dict, Optional
from pathlib import Path
import logging

from .tracer import RuntimeEvent
from ..schemas.models import NormalizedArtifact

logger = logging.getLogger(__name__)

class RuntimeNormalizer:
    """
    Normalizes runtime events into standardized AI artifacts.
    
    This class processes raw runtime events and converts them into
    NormalizedArtifact objects that can be used in the BOM generation pipeline.
    """
    
    def __init__(self):
        self.hf_patterns = [
            r'huggingface\.co/([^/]+)/([^/]+)',
            r'hf\.co/([^/]+)/([^/]+)',
            r'\.cache/huggingface/hub/([^/]+)',
            r'\.transformers_cache/([^/]+)'
        ]
    
    def normalize_events(self, events: List[RuntimeEvent]) -> List[NormalizedArtifact]:
        """
        Normalize a list of runtime events into AI artifacts.
        
        Args:
            events: List of runtime events to normalize
            
        Returns:
            List of normalized AI artifacts
        """
        artifacts = []
        seen_artifacts = set()  # Deduplicate by canonical ID
        
        for event in events:
            try:
                artifact = self._normalize_single_event(event)
                if artifact and artifact.id not in seen_artifacts:
                    artifacts.append(artifact)
                    seen_artifacts.add(artifact.id)
                    
            except Exception as e:
                logger.error(f"Failed to normalize event {event}: {e}")
                continue
        
        logger.info(f"Normalized {len(events)} events into {len(artifacts)} unique artifacts")
        return artifacts
    
    def _normalize_single_event(self, event: RuntimeEvent) -> Optional[NormalizedArtifact]:
        """Normalize a single runtime event into an AI artifact."""
        
        # Extract basic information
        path = event.path
        artifact_type = event.artifact_type or self._infer_type(path)
        
        # Skip if not a recognized AI artifact
        if artifact_type == 'unknown':
            return None
        
        # Extract name and version
        name, version = self._extract_name_version(path)
        if not name:
            return None
        
        # Determine provider
        provider = self._extract_provider(path, event.source_url)
        
        # Generate content hash
        content_hash = self._generate_content_hash(event)
        
        # Extract license information
        license_spdx = self._extract_license(path, event.metadata)
        
        # Generate canonical ID
        canonical_id = f"runtime:{name}:{artifact_type}:{provider}:{version}"
        
        # Create metadata
        metadata = {
            "runtime_detected": True,
            "process_name": event.process_name,
            "pid": event.pid,
            "syscall": event.syscall,
            "timestamp": event.timestamp,
            "source_url": event.source_url
        }
        
        if event.metadata:
            metadata.update(event.metadata)
        
        return NormalizedArtifact(
            id=canonical_id,
            kind=artifact_type,
            name=name,
            version=version,
            provider=provider,
            license_spdx=license_spdx,
            file_path=path,
            content_hash=content_hash,
            commit_sha=None,  # Not available for runtime events
            metadata=metadata
        )
    
    def _infer_type(self, path: str) -> str:
        """Infer artifact type from file path."""
        path_lower = path.lower()
        
        # Model indicators
        model_patterns = [
            r'model\.(pt|pth|bin|safetensors|onnx|pb|h5)$',
            r'pytorch_model\.(bin|safetensors)$',
            r'model\.onnx$',
            r'saved_model\.pb$',
            r'checkpoint.*\.(pt|pth|bin)$'
        ]
        
        for pattern in model_patterns:
            if re.search(pattern, path_lower):
                return 'model'
        
        # Dataset indicators
        dataset_patterns = [
            r'\.(csv|parquet|arrow|feather|jsonl)$',
            r'(train|test|valid|eval).*\.(csv|json|txt)$',
            r'dataset.*\.(csv|json|parquet)$'
        ]
        
        for pattern in dataset_patterns:
            if re.search(pattern, path_lower):
                return 'dataset'
        
        # Prompt indicators
        prompt_patterns = [
            r'\.(prompt|txt)$',
            r'(prompt|template|instruction).*\.txt$',
            r'system_prompt\.',
            r'chat_template\.'
        ]
        
        for pattern in prompt_patterns:
            if re.search(pattern, path_lower):
                return 'prompt'
        
        # Tool/config indicators
        tool_patterns = [
            r'config\.json$',
            r'tokenizer.*\.json$',
            r'vocab\.(txt|json)$',
            r'special_tokens_map\.json$',
            r'generation_config\.json$'
        ]
        
        for pattern in tool_patterns:
            if re.search(pattern, path_lower):
                return 'tool'
        
        return 'unknown'
    
    def _extract_name_version(self, path: str) -> tuple[str, str]:
        """Extract name and version from file path."""
        
        # Try HuggingFace patterns first
        for pattern in self.hf_patterns:
            match = re.search(pattern, path)
            if match:
                if len(match.groups()) >= 2:
                    org, repo = match.groups()[:2]
                    name = f"{org}/{repo}"
                    version = "latest"  # Default for HF models
                    return name, version
                elif len(match.groups()) == 1:
                    # Cache directory pattern
                    cache_name = match.group(1)
                    # Extract model name from cache directory
                    if '--' in cache_name:
                        parts = cache_name.split('--')
                        if len(parts) >= 2:
                            name = f"{parts[0]}/{parts[1]}"
                            version = "latest"
                            return name, version
        
        # Try to extract from file path
        path_obj = Path(path)
        
        # Look for version patterns in path
        version_match = re.search(r'v?(\d+\.\d+(?:\.\d+)?)', path)
        version = version_match.group(1) if version_match else "unknown"
        
        # Extract name from filename or parent directory
        filename = path_obj.stem
        
        # Remove common suffixes
        name = re.sub(r'_(model|checkpoint|weights?)$', '', filename)
        name = re.sub(r'\.(pt|pth|bin|safetensors|onnx|pb|h5)$', '', name)
        
        # If name is too generic, try parent directory
        if name in ['model', 'checkpoint', 'weights', 'pytorch_model']:
            parent_name = path_obj.parent.name
            if parent_name and parent_name not in ['.', '..', 'models', 'checkpoints']:
                name = parent_name
        
        # Clean up name
        name = re.sub(r'[^a-zA-Z0-9_\-/]', '_', name)
        
        return name or "unknown", version
    
    def _extract_provider(self, path: str, source_url: Optional[str]) -> str:
        """Extract provider information from path or URL."""
        
        # Check source URL first
        if source_url:
            if 'huggingface.co' in source_url or 'hf.co' in source_url:
                return 'huggingface'
            elif 'openai.com' in source_url:
                return 'openai'
            elif 'googleapis.com' in source_url:
                return 'google'
            elif 'anthropic.com' in source_url:
                return 'anthropic'
        
        # Check path patterns
        path_lower = path.lower()
        
        if any(pattern in path_lower for pattern in [
            'huggingface', 'hf.co', '.cache/huggingface', '.transformers_cache'
        ]):
            return 'huggingface'
        
        if 'openai' in path_lower:
            return 'openai'
        
        if any(pattern in path_lower for pattern in ['google', 'gemini', 'palm']):
            return 'google'
        
        if 'anthropic' in path_lower:
            return 'anthropic'
        
        # Check for local/custom models
        if any(pattern in path_lower for pattern in [
            '/models/', '/checkpoints/', '/weights/', 'local'
        ]):
            return 'local'
        
        return 'unknown'
    
    def _generate_content_hash(self, event: RuntimeEvent) -> str:
        """Generate a content hash for the runtime event."""
        
        # For runtime events, we can't always read file content
        # So we generate a hash based on available metadata
        hash_input = f"{event.path}:{event.timestamp}:{event.pid}"
        
        if event.metadata:
            hash_input += f":{json.dumps(event.metadata, sort_keys=True)}"
        
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _extract_license(self, path: str, metadata: Optional[Dict]) -> Optional[str]:
        """Extract license information from path or metadata."""
        
        # Check metadata first
        if metadata and 'license' in metadata:
            license_info = metadata['license']
            if isinstance(license_info, str):
                return self._normalize_license(license_info)
        
        # For HuggingFace models, we might need to fetch license info
        # This would require additional API calls, so we'll mark as unknown for now
        
        # Check for common license files in the same directory
        path_obj = Path(path)
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'license.txt']
        
        for license_file in license_files:
            license_path = path_obj.parent / license_file
            if license_path.exists():
                try:
                    with open(license_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        return self._detect_license_from_content(content)
                except Exception:
                    continue
        
        return None
    
    def _normalize_license(self, license_str: str) -> str:
        """Normalize license string to SPDX identifier."""
        license_lower = license_str.lower().strip()
        
        # Common license mappings
        license_map = {
            'mit': 'MIT',
            'apache-2.0': 'Apache-2.0',
            'apache 2.0': 'Apache-2.0',
            'bsd-3-clause': 'BSD-3-Clause',
            'bsd-2-clause': 'BSD-2-Clause',
            'gpl-3.0': 'GPL-3.0-only',
            'gpl-2.0': 'GPL-2.0-only',
            'lgpl-3.0': 'LGPL-3.0-only',
            'mpl-2.0': 'MPL-2.0',
            'cc-by-4.0': 'CC-BY-4.0',
            'cc-by-sa-4.0': 'CC-BY-SA-4.0',
            'unlicense': 'Unlicense'
        }
        
        return license_map.get(license_lower, license_str)
    
    def _detect_license_from_content(self, content: str) -> Optional[str]:
        """Detect license from file content."""
        content_lower = content.lower()
        
        if 'mit license' in content_lower:
            return 'MIT'
        elif 'apache license' in content_lower and '2.0' in content_lower:
            return 'Apache-2.0'
        elif 'bsd license' in content_lower:
            if '3-clause' in content_lower or 'three clause' in content_lower:
                return 'BSD-3-Clause'
            elif '2-clause' in content_lower or 'two clause' in content_lower:
                return 'BSD-2-Clause'
            else:
                return 'BSD-3-Clause'  # Default to 3-clause
        elif 'gnu general public license' in content_lower:
            if 'version 3' in content_lower or 'v3' in content_lower:
                return 'GPL-3.0-only'
            elif 'version 2' in content_lower or 'v2' in content_lower:
                return 'GPL-2.0-only'
        
        return None