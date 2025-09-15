#!/usr/bin/env python3
"""
Test script for Diff Engine functionality
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.diff.engine import DiffEngine
from core.schemas.models import BOM

def create_test_boms():
    """Create test BOMs for diff testing"""
    
    # BOM v1 - Initial version
    bom_v1 = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": "2024-01-01T10:00:00Z"
        },
        "components": [
            {
                "type": "machine-learning-model",
                "name": "llama-2-7b",
                "version": "v1.0",
                "properties": [
                    {"name": "provider", "value": "huggingface"},
                    {"name": "license", "value": "MIT"}
                ]
            },
            {
                "type": "data",
                "name": "common-crawl",
                "version": "2023-06",
                "properties": [
                    {"name": "license", "value": "Apache-2.0"}
                ]
            }
        ]
    }
    
    # BOM v2 - Updated version with changes
    bom_v2 = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": "2024-01-02T10:00:00Z"  # Different timestamp (should be ignored)
        },
        "components": [
            {
                "type": "machine-learning-model",
                "name": "llama-2-70b",  # Changed from 7b to 70b
                "version": "v2.0",      # Version bump
                "properties": [
                    {"name": "provider", "value": "huggingface"},
                    {"name": "license", "value": "GPL-3.0"}  # License change
                ]
            },
            {
                "type": "data",
                "name": "common-crawl",
                "version": "2023-06",
                "properties": [
                    {"name": "license", "value": "Apache-2.0"}
                ]
            },
            {
                "type": "file",
                "name": "system-prompt",  # New component
                "version": "v1.0",
                "properties": [
                    {"name": "type", "value": "prompt"},
                    {"name": "path", "value": "/prompts/system.txt"}
                ]
            }
        ]
    }
    
    return (
        BOM(id=1, project_id=1, bom_json=bom_v1, created_at=datetime(2024, 1, 1, 10, 0, 0)),
        BOM(id=2, project_id=1, bom_json=bom_v2, created_at=datetime(2024, 1, 2, 10, 0, 0))
    )

def test_component_id_generation():
    """Test component ID generation"""
    print("🧪 Testing Component ID Generation...")
    
    engine = DiffEngine()
    
    # Test component with provider
    component_with_provider = {
        "name": "llama-2-7b",
        "type": "machine-learning-model",
        "properties": [
            {"name": "provider", "value": "huggingface"}
        ]
    }
    
    comp_id = engine._get_component_id(component_with_provider)
    expected_id = "llama-2-7b:machine-learning-model:huggingface"
    
    if comp_id == expected_id:
        print(f"   ✅ Component ID with provider: {comp_id}")
    else:
        print(f"   ❌ Expected: {expected_id}, Got: {comp_id}")
        return False
    
    # Test component without provider
    component_without_provider = {
        "name": "common-crawl",
        "type": "data",
        "properties": []
    }
    
    comp_id = engine._get_component_id(component_without_provider)
    expected_id = "common-crawl:data:"
    
    if comp_id == expected_id:
        print(f"   ✅ Component ID without provider: {comp_id}")
    else:
        print(f"   ❌ Expected: {expected_id}, Got: {comp_id}")
        return False
    
    return True

def test_component_comparison():
    """Test component comparison logic"""
    print("\n🔍 Testing Component Comparison...")
    
    engine = DiffEngine()
    
    # Test version change
    old_comp = {
        "name": "llama-2-7b",
        "version": "v1.0",
        "properties": [
            {"name": "license", "value": "MIT"}
        ]
    }
    
    new_comp = {
        "name": "llama-2-7b",
        "version": "v2.0",
        "properties": [
            {"name": "license", "value": "GPL-3.0"}
        ]
    }
    
    modifications = engine._compare_components(old_comp, new_comp)
    
    print(f"   📊 Found {len(modifications)} modifications:")
    for mod in modifications:
        print(f"      - {mod['field']}: {mod['old_value']} → {mod['new_value']}")
    
    # Should detect version and license changes
    expected_changes = {'version', 'property.license'}
    actual_changes = {mod['field'] for mod in modifications}
    
    if expected_changes.issubset(actual_changes):
        print("   ✅ Component comparison: PASS")
        return True
    else:
        print(f"   ❌ Expected changes: {expected_changes}, Got: {actual_changes}")
        return False

def test_bom_diff():
    """Test full BOM diff functionality"""
    print("\n🔄 Testing BOM Diff Generation...")
    
    bom_v1, bom_v2 = create_test_boms()
    engine = DiffEngine()
    
    # Generate diff
    diff_summary = engine._compare_boms(bom_v1.bom_json, bom_v2.bom_json)
    
    print(f"   📈 Total changes: {diff_summary['stats']['total_changes']}")
    print(f"   ➕ Additions: {diff_summary['stats']['additions']}")
    print(f"   ➖ Removals: {diff_summary['stats']['removals']}")
    print(f"   🔄 Modifications: {diff_summary['stats']['modifications']}")
    
    # Check for expected changes
    changes = diff_summary['changes']
    
    # Should have: 1 removal (llama-2-7b), 1 addition (llama-2-70b), 1 addition (system-prompt)
    additions = [c for c in changes if c['type'] == 'addition']
    removals = [c for c in changes if c['type'] == 'removal']
    modifications = [c for c in changes if c['type'] == 'modification']
    
    print(f"\n   📋 Detailed changes:")
    for change in changes:
        print(f"      {change['type']}: {change.get('component_name', 'N/A')} - {change.get('details', 'N/A')}")
    
    # Validate expected changes
    if len(additions) >= 1 and len(removals) >= 1:
        print("   ✅ BOM diff generation: PASS")
        return True
    else:
        print("   ❌ BOM diff generation: Expected additions and removals")
        return False

def main():
    """Run all diff engine tests"""
    print("🚀 ML-BOM Autopilot - Diff Engine Tests")
    print("=" * 50)
    
    success = True
    
    try:
        success &= test_component_id_generation()
        success &= test_component_comparison()
        success &= test_bom_diff()
        
        if success:
            print("\n🎉 All diff engine tests passed!")
            return 0
        else:
            print("\n❌ Some diff engine tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())