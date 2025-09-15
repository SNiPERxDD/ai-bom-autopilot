#!/usr/bin/env python3
"""
Test script for Policy Engine functionality
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.policy.engine import PolicyEngine
from core.schemas.models import (
    ScanState, Project, Model, Dataset, Prompt, Tool, ToolType,
    BOM, BOMDiff, Policy, Severity
)

def create_test_scan_state():
    """Create a test scan state for policy testing"""
    project = Project(
        id=1,
        name="test-project",
        repo_url="https://github.com/test/test-project",
        default_branch="main"
    )
    
    # Model without license (should trigger missing_license)
    model_no_license = Model(
        id=1,
        project_id=1,
        name="unlicensed-model",
        provider="huggingface",
        version="v1.0",
        license=None,  # Missing license
        source_url="https://huggingface.co/test/unlicensed-model"
    )
    
    # Model with unapproved license (should trigger unapproved_license)
    model_bad_license = Model(
        id=2,
        project_id=1,
        name="bad-license-model",
        provider="huggingface",
        version="v1.0",
        license="WTFPL",  # Not in approved list
        source_url="https://huggingface.co/test/bad-license-model"
    )
    
    # Model with unknown provider (should trigger unknown_provider)
    model_unknown_provider = Model(
        id=3,
        project_id=1,
        name="unknown-model",
        provider="unknown",
        version="v1.0",
        license="MIT",
        source_url=None  # Missing source URL
    )
    
    # Dataset without license
    dataset_no_license = Dataset(
        id=1,
        project_id=1,
        name="unlicensed-dataset",
        version="v1.0",
        license=None
    )
    
    # Prompt in protected path
    prompt_protected = Prompt(
        id=1,
        project_id=1,
        name="system-prompt",
        version="v1.0",
        path="/prompts/system.txt",  # Protected path
        commit_sha="abc123",
        blob_sha="def456"
    )
    
    # Create diff with version bump
    diff_summary = {
        "changes": [
            {
                "type": "modification",
                "component_id": "test-model:machine-learning-model:huggingface",
                "component_name": "test-model",
                "field": "version",
                "old_value": "v1.0",
                "new_value": "v2.0"  # Major version bump
            },
            {
                "type": "modification",
                "component_id": "system-prompt:file:",
                "component_name": "system-prompt",
                "field": "property.blob_sha",
                "old_value": "old_sha",
                "new_value": "new_sha"  # Prompt content change
            }
        ]
    }
    
    diff = BOMDiff(
        id=1,
        project_id=1,
        from_bom=1,
        to_bom=2,
        summary=diff_summary
    )
    
    return ScanState(
        project=project,
        models=[model_no_license, model_bad_license, model_unknown_provider],
        datasets=[dataset_no_license],
        prompts=[prompt_protected],
        diff=diff
    )

def create_test_policies():
    """Create test policies"""
    return [
        Policy(
            id=1,
            rule="missing_license",
            severity=Severity.HIGH,
            spec={}
        ),
        Policy(
            id=2,
            rule="unapproved_license",
            severity=Severity.HIGH,
            spec={
                "allowed_licenses": ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0"]
            }
        ),
        Policy(
            id=3,
            rule="unknown_provider",
            severity=Severity.MEDIUM,
            spec={}
        ),
        Policy(
            id=4,
            rule="model_bump_major",
            severity=Severity.MEDIUM,
            spec={}
        ),
        Policy(
            id=5,
            rule="prompt_changed_protected_path",
            severity=Severity.HIGH,
            spec={
                "protected_paths": ["/prompts/", "/prod/"]
            }
        )
    ]

def test_missing_license_policy():
    """Test missing license policy"""
    print("🧪 Testing Missing License Policy...")
    
    engine = PolicyEngine()
    state = create_test_scan_state()
    policy = Policy(
        id=1,
        rule="missing_license",
        severity=Severity.HIGH,
        spec={}
    )
    
    events = engine._check_missing_license(state, policy)
    
    print(f"   📊 Generated {len(events)} events")
    
    # Should find 2 events: 1 model + 1 dataset without license
    expected_events = 2
    if len(events) == expected_events:
        print("   ✅ Missing license policy: PASS")
        for event in events:
            print(f"      - {event.artifact['type']}: {event.artifact['name']}")
        return True
    else:
        print(f"   ❌ Expected {expected_events} events, got {len(events)}")
        return False

def test_unapproved_license_policy():
    """Test unapproved license policy"""
    print("\n🚫 Testing Unapproved License Policy...")
    
    engine = PolicyEngine()
    state = create_test_scan_state()
    policy = Policy(
        id=2,
        rule="unapproved_license",
        severity=Severity.HIGH,
        spec={
            "allowed_licenses": ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0"]
        }
    )
    
    events = engine._check_unapproved_license(state, policy)
    
    print(f"   📊 Generated {len(events)} events")
    
    # Should find 1 event: model with WTFPL license
    expected_events = 1
    if len(events) == expected_events:
        print("   ✅ Unapproved license policy: PASS")
        for event in events:
            print(f"      - {event.artifact['type']}: {event.artifact['name']} ({event.artifact['license']})")
        return True
    else:
        print(f"   ❌ Expected {expected_events} events, got {len(events)}")
        return False

def test_unknown_provider_policy():
    """Test unknown provider policy"""
    print("\n❓ Testing Unknown Provider Policy...")
    
    engine = PolicyEngine()
    state = create_test_scan_state()
    policy = Policy(
        id=3,
        rule="unknown_provider",
        severity=Severity.MEDIUM,
        spec={}
    )
    
    events = engine._check_unknown_provider(state, policy)
    
    print(f"   📊 Generated {len(events)} events")
    
    # Should find 1 event: model with unknown provider
    expected_events = 1
    if len(events) == expected_events:
        print("   ✅ Unknown provider policy: PASS")
        for event in events:
            print(f"      - {event.artifact['type']}: {event.artifact['name']} (provider: {event.artifact['provider']})")
        return True
    else:
        print(f"   ❌ Expected {expected_events} events, got {len(events)}")
        return False

def test_version_bump_policy():
    """Test major version bump policy"""
    print("\n📈 Testing Version Bump Policy...")
    
    engine = PolicyEngine()
    state = create_test_scan_state()
    policy = Policy(
        id=4,
        rule="model_bump_major",
        severity=Severity.MEDIUM,
        spec={}
    )
    
    # Debug: print the diff summary
    if state.diff:
        print(f"   🔍 Diff changes: {len(state.diff.summary.get('changes', []))}")
        for change in state.diff.summary.get('changes', []):
            print(f"      - {change.get('type')}: {change.get('field')} = {change.get('old_value')} → {change.get('new_value')}")
            if change.get('field') == 'version':
                is_major = engine._is_major_version_bump(change.get('old_value'), change.get('new_value'))
                print(f"        Major bump: {is_major}")
    
    events = engine._check_model_bump_major(state, policy)
    
    print(f"   📊 Generated {len(events)} events")
    
    # Should find 1 event: version change from v1.0 to v2.0
    expected_events = 1
    if len(events) == expected_events:
        print("   ✅ Version bump policy: PASS")
        for event in events:
            print(f"      - {event.details['message']}")
        return True
    else:
        print(f"   ❌ Expected {expected_events} events, got {len(events)}")
        return False

def test_prompt_change_policy():
    """Test prompt change in protected path policy"""
    print("\n📝 Testing Prompt Change Policy...")
    
    engine = PolicyEngine()
    state = create_test_scan_state()
    policy = Policy(
        id=5,
        rule="prompt_changed_protected_path",
        severity=Severity.HIGH,
        spec={
            "protected_paths": ["/prompts/", "/prod/"]
        }
    )
    
    events = engine._check_prompt_changed_protected_path(state, policy)
    
    print(f"   📊 Generated {len(events)} events")
    
    # Should find 1 event: prompt change in /prompts/ path
    expected_events = 1
    if len(events) == expected_events:
        print("   ✅ Prompt change policy: PASS")
        for event in events:
            print(f"      - {event.details['message']}")
        return True
    else:
        print(f"   ❌ Expected {expected_events} events, got {len(events)}")
        return False

def test_dedupe_key_generation():
    """Test deduplication key generation"""
    print("\n🔑 Testing Dedupe Key Generation...")
    
    engine = PolicyEngine()
    
    # Test consistent key generation
    key1 = engine._generate_dedupe_key("missing_license", "model", "test-model")
    key2 = engine._generate_dedupe_key("missing_license", "model", "test-model")
    
    if key1 == key2:
        print(f"   ✅ Consistent dedupe keys: {key1}")
    else:
        print(f"   ❌ Inconsistent dedupe keys: {key1} != {key2}")
        return False
    
    # Test different keys for different inputs
    key3 = engine._generate_dedupe_key("missing_license", "model", "different-model")
    
    if key1 != key3:
        print(f"   ✅ Different dedupe keys for different inputs")
        return True
    else:
        print(f"   ❌ Same dedupe key for different inputs")
        return False

def test_version_bump_detection():
    """Test version bump detection logic"""
    print("\n🔍 Testing Version Bump Detection...")
    
    engine = PolicyEngine()
    
    test_cases = [
        ("v1.0", "v2.0", True),   # Major bump
        ("1.0", "2.0", True),     # Major bump without 'v'
        ("v1.5", "v1.6", False), # Minor bump
        ("v2.1", "v2.2", False), # Patch bump
        ("invalid", "v2.0", False), # Invalid old version
        ("v1.0", "invalid", False), # Invalid new version
    ]
    
    all_passed = True
    for old_ver, new_ver, expected in test_cases:
        result = engine._is_major_version_bump(old_ver, new_ver)
        if result == expected:
            print(f"   ✅ {old_ver} → {new_ver}: {result}")
        else:
            print(f"   ❌ {old_ver} → {new_ver}: Expected {expected}, got {result}")
            all_passed = False
    
    return all_passed

def main():
    """Run all policy engine tests"""
    print("🚀 ML-BOM Autopilot - Policy Engine Tests")
    print("=" * 50)
    
    success = True
    
    try:
        success &= test_missing_license_policy()
        success &= test_unapproved_license_policy()
        success &= test_unknown_provider_policy()
        success &= test_version_bump_policy()
        success &= test_prompt_change_policy()
        success &= test_dedupe_key_generation()
        success &= test_version_bump_detection()
        
        if success:
            print("\n🎉 All policy engine tests passed!")
            return 0
        else:
            print("\n❌ Some policy engine tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())