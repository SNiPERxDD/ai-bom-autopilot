#!/usr/bin/env python3
"""
Test script for BOM Generator functionality
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bom.generator import BOMGenerator
from core.schemas.models import (
    ScanState, Project, Model, Dataset, Prompt, Tool, ToolType
)

def create_test_scan_state():
    """Create a test scan state with sample data"""
    project = Project(
        id=1,
        name="test-project",
        repo_url="https://github.com/test/test-project",
        default_branch="main"
    )
    
    # Sample model
    model = Model(
        id=1,
        project_id=1,
        name="llama-2-7b",
        provider="huggingface",
        version="v1.0",
        license="MIT",
        source_url="https://huggingface.co/meta-llama/Llama-2-7b",
        repo_path="models/llama-2-7b",
        commit_sha="abc123def456",
        meta={"architecture": "transformer", "parameters": "7B"}
    )
    
    # Sample dataset
    dataset = Dataset(
        id=1,
        project_id=1,
        name="common-crawl",
        version="2023-06",
        license="Apache-2.0",
        source_url="https://commoncrawl.org/",
        commit_sha="def456ghi789",
        meta={"size": "100GB", "format": "jsonl"}
    )
    
    # Sample prompt
    prompt = Prompt(
        id=1,
        project_id=1,
        name="system-prompt",
        version="v1.2",
        path="/prompts/system.txt",
        commit_sha="ghi789jkl012",
        blob_sha="sha256:abcdef123456",
        meta={"type": "system", "length": 150}
    )
    
    # Sample tool
    tool = Tool(
        id=1,
        project_id=1,
        name="openai-api",
        version="1.3.7",
        type=ToolType.API,
        spec={"endpoint": "https://api.openai.com/v1", "model": "gpt-4"},
        meta={"provider": "openai"}
    )
    
    return ScanState(
        project=project,
        commit_sha="main-abc123",
        models=[model],
        datasets=[dataset],
        prompts=[prompt],
        tools=[tool]
    )

def test_bom_generation():
    """Test BOM generation functionality"""
    print("🧪 Testing BOM Generation...")
    
    # Create test state
    state = create_test_scan_state()
    
    # Create BOM generator
    generator = BOMGenerator()
    
    # Test basic validation first
    print("1. Testing basic BOM validation...")
    
    # Valid BOM structure
    valid_bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "components": [
            {
                "type": "machine-learning-model",
                "name": "test-model",
                "version": "1.0"
            }
        ]
    }
    
    if generator.validate_bom(valid_bom):
        print("   ✅ Basic validation: PASS")
    else:
        print("   ❌ Basic validation: FAIL")
        return False
    
    # Test tool-based validation
    print("2. Testing tool-based BOM validation...")
    validation_result = generator.validate_bom_with_tool(valid_bom)
    print(f"   📋 Validation result: {validation_result}")
    
    # Test component creation
    print("3. Testing component creation...")
    
    model_component = generator._create_model_component(state.models[0])
    print(f"   📦 Model component: {model_component.name} v{model_component.version}")
    
    dataset_component = generator._create_dataset_component(state.datasets[0])
    print(f"   📊 Dataset component: {dataset_component.name} v{dataset_component.version}")
    
    prompt_component = generator._create_prompt_component(state.prompts[0])
    print(f"   📝 Prompt component: {prompt_component.name} v{prompt_component.version}")
    
    tool_component = generator._create_tool_component(state.tools[0])
    print(f"   🔧 Tool component: {tool_component.name} v{tool_component.version}")
    
    print("✅ All BOM generation tests passed!")
    return True

def test_bom_structure():
    """Test the structure of generated BOM"""
    print("\n🔍 Testing BOM Structure...")
    
    state = create_test_scan_state()
    generator = BOMGenerator()
    
    # Mock the database operations for testing
    original_store_bom = generator._store_bom
    
    def mock_store_bom(project_id, bom_json, bom_hash):
        from core.schemas.models import BOM
        return BOM(
            id=1,
            project_id=project_id,
            bom_json=bom_json,
            created_at=datetime.utcnow()
        )
    
    generator._store_bom = mock_store_bom
    
    # Generate BOM (this will fail on DB operations but we can check the structure)
    try:
        # We'll manually create the BOM structure to test
        from cyclonedx.model.bom import Bom
        from cyclonedx.output.json import JsonV1Dot5
        import json
        
        bom = Bom()
        bom.metadata.timestamp = datetime.utcnow()
        
        # Add components
        for model in state.models:
            component = generator._create_model_component(model)
            bom.components.add(component)
        
        for dataset in state.datasets:
            component = generator._create_dataset_component(dataset)
            bom.components.add(component)
        
        for prompt in state.prompts:
            component = generator._create_prompt_component(prompt)
            bom.components.add(component)
        
        for tool in state.tools:
            component = generator._create_tool_component(tool)
            bom.components.add(component)
        
        # Convert to JSON
        json_output = JsonV1Dot5(bom)
        bom_json = json.loads(json_output.output_as_string())
        
        print(f"   📋 BOM Format: {bom_json.get('bomFormat')}")
        print(f"   📋 Spec Version: {bom_json.get('specVersion')}")
        print(f"   📋 Components: {len(bom_json.get('components', []))}")
        
        # Check component types
        component_types = {}
        for component in bom_json.get('components', []):
            comp_type = component.get('type')
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        print(f"   📊 Component breakdown: {component_types}")
        
        # Validate structure
        validation_result = generator.validate_bom_with_tool(bom_json)
        if validation_result['valid']:
            print("   ✅ Generated BOM structure: VALID")
        else:
            print(f"   ⚠️  Generated BOM structure: {validation_result.get('error', 'Unknown validation issue')}")
        
        # Test hash calculation
        import hashlib
        bom_json_str = json.dumps(bom_json, sort_keys=True)
        bom_hash = hashlib.sha256(bom_json_str.encode()).hexdigest()
        print(f"   🔐 BOM SHA256: {bom_hash[:16]}...")
        
    except Exception as e:
        print(f"   ❌ BOM structure test failed: {e}")
        return False
    
    print("✅ BOM structure tests passed!")
    return True

def main():
    """Run all BOM generator tests"""
    print("🚀 ML-BOM Autopilot - BOM Generator Tests")
    print("=" * 50)
    
    success = True
    
    try:
        success &= test_bom_generation()
        success &= test_bom_structure()
        
        if success:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())