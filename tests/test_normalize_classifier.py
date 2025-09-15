#!/usr/bin/env python3
"""
Test script for the enhanced ArtifactClassifier
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

def test_canonical_id_generation():
    """Test canonical ID generation"""
    classifier = ArtifactClassifier()
    
    # Test basic ID generation
    canonical_id = classifier._generate_canonical_id(
        "my-project", "llama-2-7b", "model", "meta", "2.0"
    )
    expected = "my_project:llama_2_7b:model:meta:2.0"
    assert canonical_id == expected, f"Expected {expected}, got {canonical_id}"
    
    # Test with special characters
    canonical_id = classifier._generate_canonical_id(
        "My Project!", "GPT-3.5/turbo", "model", "OpenAI Inc.", "v1.0-beta"
    )
    expected = "my_project_:gpt_3_5_turbo:model:openai_inc_:v1.0_beta"
    assert canonical_id == expected, f"Expected {expected}, got {canonical_id}"
    
    print("✓ Canonical ID generation tests passed")

def test_license_normalization():
    """Test enhanced license normalization"""
    classifier = ArtifactClassifier()
    
    # Test known licenses
    license, is_unknown = classifier._normalize_license_enhanced("MIT")
    assert license == "MIT" and not is_unknown
    
    license, is_unknown = classifier._normalize_license_enhanced("apache-2.0")
    assert license == "Apache-2.0" and not is_unknown
    
    # Test unknown license
    license, is_unknown = classifier._normalize_license_enhanced("Custom Proprietary License")
    assert is_unknown, "Should flag unknown license"
    
    # Test None license
    license, is_unknown = classifier._normalize_license_enhanced(None)
    assert license is None and is_unknown
    
    # Test file-based license detection
    test_file = Path("test_license_file.py")
    if test_file.exists():
        license, is_unknown = classifier._normalize_license_enhanced(None, test_file)
        assert license == "MIT" and not is_unknown, f"Expected MIT license from file, got {license}"
    
    print("✓ License normalization tests passed")

def test_artifact_classification():
    """Test artifact classification with mock data"""
    classifier = ArtifactClassifier()
    
    # Create mock project and state
    project = Project(id=1, name="test-project", repo_url="https://github.com/test/repo")
    state = ScanState(project=project, commit_sha="abc123")
    
    # Create mock HF card
    hf_card = HFCard(
        slug="meta-llama/Llama-2-7b-hf",
        type="model",
        license="llama2",
        model_type="llama",
        pipeline_tag="text-generation",
        library_name="transformers",
        tags=["llama", "text-generation"]
    )
    
    # Test model creation
    model = classifier._create_model_from_hf(1, "meta-llama/Llama-2-7b-hf", hf_card, "abc123")
    assert model is not None
    assert model.name == "Llama-2-7b-hf"
    assert model.provider == "meta"
    assert "canonical_id" in model.meta
    assert "license_unknown" in model.meta
    
    print("✓ Artifact classification tests passed")

def test_prompt_extraction():
    """Test prompt extraction from files"""
    classifier = ArtifactClassifier()
    
    # Create a temporary file with prompts
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
# Test file with prompts
system_prompt = """You are a helpful AI assistant. Please provide accurate and helpful responses to user questions."""

user_prompt = "What is the capital of France?"

PROMPT = """This is a constant prompt that should be detected by the classifier."""
''')
        temp_file = Path(f.name)
    
    try:
        prompts = classifier._extract_prompts_from_file(1, "test.py", temp_file, "abc123")
        assert len(prompts) >= 2, f"Expected at least 2 prompts, got {len(prompts)}"
        
        # Check that canonical IDs are generated
        for prompt in prompts:
            assert "canonical_id" in prompt.meta
            assert "license_unknown" in prompt.meta
        
        print(f"✓ Prompt extraction tests passed ({len(prompts)} prompts found)")
        
    finally:
        temp_file.unlink()

def test_tool_extraction():
    """Test tool extraction from files"""
    classifier = ArtifactClassifier()
    
    # Create a temporary Python file with tools
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
from fastapi import FastAPI

app = FastAPI()

def api_call_handler(request):
    """Handle API calls"""
    pass

class APIClient:
    """API client class"""
    pass

@app.get("/health")
def health_endpoint():
    return {"status": "ok"}
''')
        temp_file = Path(f.name)
    
    try:
        tools = classifier._extract_tools_from_file(1, "test.py", temp_file, "abc123")
        assert len(tools) >= 2, f"Expected at least 2 tools, got {len(tools)}"
        
        # Check that canonical IDs are generated
        for tool in tools:
            assert "canonical_id" in tool.meta
            assert "license_unknown" in tool.meta
        
        print(f"✓ Tool extraction tests passed ({len(tools)} tools found)")
        
    finally:
        temp_file.unlink()

def main():
    """Run all tests"""
    print("Testing Enhanced ArtifactClassifier...")
    
    try:
        test_canonical_id_generation()
        test_license_normalization()
        test_artifact_classification()
        test_prompt_extraction()
        test_tool_extraction()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()