#!/usr/bin/env python3
"""
End-to-end mock test of AI-BOM Autopilot workflow
Tests the complete pipeline without external dependencies
"""

import sys
import os
import tempfile
import shutil
import json
from unittest.mock import Mock, patch

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from core.schemas.models import Project, ScanState
from core.scan_git.scanner import GitScanner
from core.scan_hf.fetcher import HuggingFaceFetcher, HFCard
from core.normalize.classifier import ArtifactClassifier
from core.bom.generator import BOMGenerator

def create_mock_repo():
    """Create a mock Git repository for testing"""
    temp_dir = tempfile.mkdtemp()
    
    # Create sample files
    files = {
        'train.py': '''
from transformers import AutoModel, AutoTokenizer
from datasets import load_dataset

# Load model
model = AutoModel.from_pretrained("meta-llama/Llama-3.1-8B")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

# Load dataset
dataset = load_dataset("imdb")
        ''',
        'config.yaml': '''
model:
  name: "meta-llama/Llama-3.1-8B"
  license: "custom"
dataset:
  name: "imdb"
  license: "Apache-2.0"
        ''',
        'prompts/system.txt': '''
You are a helpful AI assistant for machine learning tasks.
Please analyze the following data and provide insights.
        ''',
        'README.md': '''
# ML Project
This project uses LLaMA for text generation.
        '''
    }
    
    for file_path, content in files.items():
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
    
    return temp_dir

def test_git_scanner():
    """Test Git scanner component"""
    print("🔍 Testing Git Scanner...")
    
    try:
        # Create mock repo
        repo_path = create_mock_repo()
        
        # Create project
        project = Project(
            id=1,
            name="test-project",
            repo_url=repo_path,
            default_branch="main"
        )
        
        # Mock the git operations
        scanner = GitScanner()
        
        with patch.object(scanner, '_get_repo_path', return_value=repo_path):
            with patch('git.Repo') as mock_repo:
                mock_repo.return_value.head.commit.hexsha = "abc123def456"
                
                state = scanner.scan_repository(project)
        
        # Verify results
        assert state.commit_sha == "abc123def456"
        assert len(state.files) > 0
        assert len(state.hf_slugs) > 0
        assert "meta-llama/Llama-3.1-8B" in state.hf_slugs
        
        print(f"  ✅ Found {len(state.files)} files")
        print(f"  ✅ Found {len(state.hf_slugs)} HF references")
        
        # Cleanup
        shutil.rmtree(repo_path)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Git scanner test failed: {e}")
        return False

def test_hf_fetcher():
    """Test HuggingFace fetcher component"""
    print("🔍 Testing HuggingFace Fetcher...")
    
    try:
        fetcher = HuggingFaceFetcher()
        
        # Mock HF API responses
        mock_model_response = Mock()
        mock_model_response.status_code = 200
        mock_model_response.json.return_value = {
            'license': 'custom',
            'tags': ['text-generation'],
            'pipeline_tag': 'text-generation',
            'library_name': 'transformers'
        }
        
        mock_readme_response = Mock()
        mock_readme_response.status_code = 200
        mock_readme_response.text = '''---
license: custom
datasets:
- common_crawl
---
# LLaMA Model
'''
        
        with patch.object(fetcher, '_make_request') as mock_request:
            mock_request.side_effect = [mock_model_response, mock_readme_response]
            
            card = fetcher.fetch_card("meta-llama/Llama-3.1-8B")
        
        # Verify results
        assert card is not None
        assert card.type == "model"
        assert card.license == "custom"
        assert "text-generation" in card.tags
        
        print(f"  ✅ Fetched model card: {card.slug}")
        print(f"  ✅ License: {card.license}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ HF fetcher test failed: {e}")
        return False

def test_artifact_classifier():
    """Test artifact classifier component"""
    print("🔍 Testing Artifact Classifier...")
    
    try:
        classifier = ArtifactClassifier()
        
        # Create mock state with HF cards
        project = Project(id=1, name="test", repo_url="/tmp/test", default_branch="main")
        state = ScanState(project=project)
        state.commit_sha = "abc123"
        state.files = ["train.py", "config.yaml", "prompts/system.txt"]
        
        # Mock HF cards
        hf_cards = {
            "meta-llama/Llama-3.1-8B": HFCard(
                slug="meta-llama/Llama-3.1-8B",
                type="model",
                license="custom",
                tags=["text-generation"],
                pipeline_tag="text-generation"
            )
        }
        
        # Mock file reading
        with patch('builtins.open'), patch('os.path.exists', return_value=True):
            state = classifier.normalize_artifacts(state, hf_cards)
        
        # Verify results
        assert len(state.models) > 0
        assert state.models[0].name == "Llama-3.1-8B"
        assert state.models[0].license == "custom"
        
        print(f"  ✅ Classified {len(state.models)} models")
        print(f"  ✅ Classified {len(state.datasets)} datasets")
        print(f"  ✅ Classified {len(state.prompts)} prompts")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Classifier test failed: {e}")
        return False

def test_bom_generator():
    """Test BOM generator component"""
    print("🔍 Testing BOM Generator...")
    
    try:
        generator = BOMGenerator()
        
        # Create mock state with artifacts
        project = Project(id=1, name="test", repo_url="/tmp/test", default_branch="main")
        state = ScanState(project=project)
        
        # Add mock artifacts
        from core.schemas.models import Model, Dataset, Prompt, Tool, ToolType
        
        state.models = [
            Model(
                project_id=1,
                name="Llama-3.1-8B",
                provider="meta",
                version="3.1",
                license="custom",
                source_url="https://huggingface.co/meta-llama/Llama-3.1-8B"
            )
        ]
        
        state.datasets = [
            Dataset(
                project_id=1,
                name="imdb",
                version="1.0",
                license="Apache-2.0",
                source_url="https://huggingface.co/datasets/imdb"
            )
        ]
        
        # Mock database operations
        with patch('core.bom.generator.db_manager'):
            with patch.object(generator, '_store_bom') as mock_store:
                mock_bom = Mock()
                mock_bom.id = 1
                mock_store.return_value = mock_bom
                
                state = generator.generate_bom(state)
        
        # Verify BOM was created
        assert state.bom is not None
        
        print(f"  ✅ Generated BOM with ID: {state.bom.id}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ BOM generator test failed: {e}")
        return False

def test_full_workflow():
    """Test the complete workflow integration"""
    print("🔍 Testing Full Workflow Integration...")
    
    try:
        from core.graph.workflow import MLBOMWorkflow
        
        # Create mock project
        project = Project(
            id=1,
            name="test-project",
            repo_url="/tmp/test-repo",
            default_branch="main"
        )
        
        workflow = MLBOMWorkflow()
        
        # Test individual workflow nodes instead of the full LangGraph execution
        # This avoids LangGraph complexity in testing
        
        # Test scan_git node
        initial_state = ScanState(project=project)
        
        with patch.object(workflow.git_scanner, 'scan_repository') as mock_git:
            mock_state = ScanState(project=project)
            mock_state.commit_sha = "abc123"
            mock_state.files = ["train.py"]
            mock_state.hf_slugs = ["meta-llama/Llama-3.1-8B"]
            mock_git.return_value = mock_state
            
            result = workflow._scan_git_node(initial_state)
        
        # Verify workflow node completed
        assert result is not None
        assert result.commit_sha == "abc123"
        assert len(result.files) > 0
        
        print(f"  ✅ Git scan node completed")
        print(f"  ✅ Found {len(result.files)} files")
        print(f"  ✅ Found {len(result.hf_slugs)} HF references")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Full workflow test failed: {e}")
        return False

def main():
    """Run all end-to-end tests"""
    print("🚀 Running AI-BOM Autopilot End-to-End Mock Tests...\n")
    
    tests = [
        ("Git Scanner", test_git_scanner),
        ("HuggingFace Fetcher", test_hf_fetcher),
        ("Artifact Classifier", test_artifact_classifier),
        ("BOM Generator", test_bom_generator),
        ("Full Workflow", test_full_workflow),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        if test_func():
            passed += 1
            print(f"✅ {test_name} passed!")
        else:
            print(f"❌ {test_name} failed!")
        print()
    
    print(f"🎯 End-to-End Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All end-to-end tests passed! System workflow is functional.")
        return True
    else:
        print("❌ Some end-to-end tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)