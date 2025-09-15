#!/usr/bin/env python3
"""
Integration test for the enhanced ArtifactClassifier
Tests the complete normalization workflow with real-world scenarios
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.normalize.classifier import ArtifactClassifier
from core.schemas.models import ScanState, Project
from core.scan_hf.fetcher import HFCard

def test_complete_normalization_workflow():
    """Test the complete normalization workflow"""
    classifier = ArtifactClassifier()
    
    # Create mock project and state
    project = Project(id=1, name="ml-test-project", repo_url="https://github.com/test/ml-project")
    state = ScanState(project=project, commit_sha="abc123def456")
    
    # Create mock HF cards
    hf_cards = {
        "meta-llama/Llama-2-7b-hf": HFCard(
            slug="meta-llama/Llama-2-7b-hf",
            type="model",
            license="llama2",  # This should be flagged as unknown
            model_type="llama",
            pipeline_tag="text-generation",
            library_name="transformers",
            tags=["llama", "text-generation", "7b"]
        ),
        "huggingface/CodeBERTa-small-v1": HFCard(
            slug="huggingface/CodeBERTa-small-v1",
            type="model",
            license="mit",  # This should be normalized to MIT
            model_type="roberta",
            pipeline_tag="feature-extraction",
            library_name="transformers",
            tags=["code", "bert"]
        ),
        "squad": HFCard(
            slug="squad",
            type="dataset",
            license="cc-by-4.0",  # This should be normalized to CC-BY-4.0
            model_type=None,
            pipeline_tag=None,
            library_name=None,
            tags=["question-answering", "dataset"]
        )
    }
    
    # Create temporary files to simulate repository structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a Python file with prompts and tools
        python_file = temp_path / "ai_assistant.py"
        python_file.write_text('''
# SPDX-License-Identifier: Apache-2.0
"""
AI Assistant module with prompts and API tools
"""

from fastapi import FastAPI

app = FastAPI()

# System prompts
SYSTEM_PROMPT = """You are a helpful AI assistant specialized in code analysis. 
Please provide accurate and detailed responses about code structure and functionality."""

user_prompt = """Analyze the following code and provide insights about its functionality."""

def api_call_handler(request):
    """Handle API calls for code analysis"""
    return {"status": "processed"}

class CodeAnalysisAPI:
    """API client for code analysis services"""
    
    def __init__(self):
        self.endpoint = "https://api.example.com/analyze"

@app.get("/health")
def health_endpoint():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/analyze")
def analyze_endpoint(code: str):
    """Code analysis endpoint"""
    return {"analysis": "completed"}
''')
        
        # Create a JSON configuration file
        json_file = temp_path / "mcp_tools.json"
        json_file.write_text('''
{
    "tools": {
        "code_analyzer": {
            "version": "2.1.0",
            "description": "Analyzes code structure and complexity",
            "parameters": {
                "language": "python",
                "depth": "full"
            }
        },
        "documentation_generator": {
            "version": "1.5.0",
            "description": "Generates documentation from code",
            "parameters": {
                "format": "markdown"
            }
        }
    }
}
''')
        
        # Create an OpenAPI spec file
        openapi_file = temp_path / "api_spec.json"
        openapi_file.write_text('''
{
    "openapi": "3.0.0",
    "info": {
        "title": "ML Model API",
        "version": "1.2.0",
        "description": "API for ML model inference"
    },
    "paths": {
        "/predict": {
            "post": {
                "summary": "Make predictions",
                "operationId": "predict"
            }
        }
    }
}
''')
        
        # Update state with file paths
        state.files = [
            str(python_file.relative_to(temp_path)),
            str(json_file.relative_to(temp_path)),
            str(openapi_file.relative_to(temp_path))
        ]
        
        # Mock the repository path resolution
        original_normalize = classifier.normalize_artifacts
        def mock_normalize(state, hf_cards):
            # Temporarily override file paths for testing
            for i, file_path in enumerate(state.files):
                if file_path.endswith('.py'):
                    prompts = classifier._extract_prompts_from_file(
                        state.project.id, file_path, python_file, state.commit_sha
                    )
                    state.prompts.extend(prompts)
                    
                    tools = classifier._extract_tools_from_file(
                        state.project.id, file_path, python_file, state.commit_sha
                    )
                    state.tools.extend(tools)
                
                elif file_path.endswith('.json'):
                    if 'mcp' in file_path:
                        tools = classifier._extract_tools_from_file(
                            state.project.id, file_path, json_file, state.commit_sha
                        )
                        state.tools.extend(tools)
                    elif 'api_spec' in file_path:
                        tools = classifier._extract_tools_from_file(
                            state.project.id, file_path, openapi_file, state.commit_sha
                        )
                        state.tools.extend(tools)
            
            # Process HF cards
            for slug, card in hf_cards.items():
                if card.type == 'model':
                    model = classifier._create_model_from_hf(state.project.id, slug, card, state.commit_sha)
                    if model:
                        state.models.append(model)
                elif card.type == 'dataset':
                    dataset = classifier._create_dataset_from_hf(state.project.id, slug, card, state.commit_sha)
                    if dataset:
                        state.datasets.append(dataset)
            
            return state
        
        # Run the normalization
        result_state = mock_normalize(state, hf_cards)
        
        # Verify results
        print(f"Found {len(result_state.models)} models:")
        for model in result_state.models:
            print(f"  - {model.name} ({model.provider}) - License: {model.license} (Unknown: {model.meta.get('license_unknown', False)})")
            assert 'canonical_id' in model.meta
            assert 'license_unknown' in model.meta
        
        print(f"Found {len(result_state.datasets)} datasets:")
        for dataset in result_state.datasets:
            print(f"  - {dataset.name} - License: {dataset.license} (Unknown: {dataset.meta.get('license_unknown', False)})")
            assert 'canonical_id' in dataset.meta
            assert 'license_unknown' in dataset.meta
        
        print(f"Found {len(result_state.prompts)} prompts:")
        for prompt in result_state.prompts:
            print(f"  - {prompt.name} (Pattern: {prompt.meta.get('pattern_type', 'unknown')})")
            assert 'canonical_id' in prompt.meta
            assert 'license_unknown' in prompt.meta
        
        print(f"Found {len(result_state.tools)} tools:")
        for tool in result_state.tools:
            print(f"  - {tool.name} ({tool.type}) v{tool.version}")
            assert 'canonical_id' in tool.meta
            assert 'license_unknown' in tool.meta
        
        # Verify specific expectations
        assert len(result_state.models) == 2, f"Expected 2 models, got {len(result_state.models)}"
        assert len(result_state.datasets) == 1, f"Expected 1 dataset, got {len(result_state.datasets)}"
        assert len(result_state.prompts) >= 2, f"Expected at least 2 prompts, got {len(result_state.prompts)}"
        assert len(result_state.tools) >= 5, f"Expected at least 5 tools, got {len(result_state.tools)}"
        
        # Verify license handling
        llama_model = next((m for m in result_state.models if 'llama' in m.name.lower()), None)
        assert llama_model is not None, "Llama model not found"
        assert llama_model.meta['license_unknown'] == True, "Llama license should be flagged as unknown"
        
        codeberta_model = next((m for m in result_state.models if 'codeberta' in m.name.lower()), None)
        assert codeberta_model is not None, "CodeBERTa model not found"
        assert codeberta_model.license == "MIT", f"Expected MIT license, got {codeberta_model.license}"
        assert codeberta_model.meta['license_unknown'] == False, "MIT license should not be flagged as unknown"
        
        squad_dataset = next((d for d in result_state.datasets if 'squad' in d.name.lower()), None)
        assert squad_dataset is not None, "SQuAD dataset not found"
        assert squad_dataset.license == "CC-BY-4.0", f"Expected CC-BY-4.0 license, got {squad_dataset.license}"
        
        # Verify canonical IDs are properly formatted
        for artifact in result_state.models + result_state.datasets + result_state.prompts + result_state.tools:
            canonical_id = artifact.meta['canonical_id']
            parts = canonical_id.split(':')
            assert len(parts) == 5, f"Canonical ID should have 5 parts, got {len(parts)}: {canonical_id}"
            assert all(part for part in parts), f"All parts should be non-empty: {canonical_id}"
        
        print("\n✅ Complete normalization workflow test passed!")
        return result_state

def main():
    """Run integration tests"""
    print("Running Enhanced ArtifactClassifier Integration Tests...")
    
    try:
        test_complete_normalization_workflow()
        print("\n🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()