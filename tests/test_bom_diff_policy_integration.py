#!/usr/bin/env python3
"""
Integration test for BOM, Diff, and Policy engines working together
"""

import sys
import os
import json
import hashlib
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bom.generator import BOMGenerator
from core.diff.engine import DiffEngine
from core.policy.engine import PolicyEngine
from core.schemas.models import (
    ScanState, Project, Model, Dataset, Prompt, Tool, ToolType,
    BOM, Policy, Severity
)

def create_initial_scan_state():
    """Create initial scan state (v1)"""
    project = Project(
        id=1,
        name="ml-project",
        repo_url="https://github.com/company/ml-project",
        default_branch="main"
    )
    
    # Initial model - small version
    model = Model(
        id=1,
        project_id=1,
        name="llama-2-7b",
        provider="huggingface",
        version="v1.0",
        license="MIT",
        source_url="https://huggingface.co/meta-llama/Llama-2-7b",
        repo_path="models/llama-2-7b",
        commit_sha="abc123def456"
    )
    
    # Dataset with proper license
    dataset = Dataset(
        id=1,
        project_id=1,
        name="common-crawl",
        version="2023-06",
        license="Apache-2.0",
        source_url="https://commoncrawl.org/",
        commit_sha="def456ghi789"
    )
    
    # System prompt
    prompt = Prompt(
        id=1,
        project_id=1,
        name="system-prompt",
        version="v1.0",
        path="/prompts/system.txt",
        commit_sha="ghi789jkl012",
        blob_sha="sha256:original_content"
    )
    
    return ScanState(
        project=project,
        commit_sha="main-abc123",
        models=[model],
        datasets=[dataset],
        prompts=[prompt]
    )

def create_updated_scan_state():
    """Create updated scan state (v2) with changes"""
    project = Project(
        id=1,
        name="ml-project",
        repo_url="https://github.com/company/ml-project",
        default_branch="main"
    )
    
    # Updated model - major version bump and license change
    model = Model(
        id=1,
        project_id=1,
        name="llama-2-70b",  # Changed from 7b to 70b
        provider="huggingface",
        version="v2.0",      # Major version bump
        license="GPL-3.0",   # License change
        source_url="https://huggingface.co/meta-llama/Llama-2-70b",
        repo_path="models/llama-2-70b",
        commit_sha="abc123def456"
    )
    
    # Same dataset
    dataset = Dataset(
        id=1,
        project_id=1,
        name="common-crawl",
        version="2023-06",
        license="Apache-2.0",
        source_url="https://commoncrawl.org/",
        commit_sha="def456ghi789"
    )
    
    # Updated prompt content
    prompt = Prompt(
        id=1,
        project_id=1,
        name="system-prompt",
        version="v1.1",
        path="/prompts/system.txt",  # Protected path
        commit_sha="ghi789jkl012",
        blob_sha="sha256:updated_content"  # Content changed
    )
    
    # New model without license (should trigger policy)
    new_model = Model(
        id=2,
        project_id=1,
        name="unlicensed-model",
        provider="unknown",
        version="v1.0",
        license=None,  # Missing license
        source_url=None  # Missing source URL
    )
    
    return ScanState(
        project=project,
        commit_sha="main-def456",
        models=[model, new_model],
        datasets=[dataset],
        prompts=[prompt]
    )

def mock_store_bom(generator, project_id, bom_json, bom_hash):
    """Mock BOM storage for testing"""
    # Simulate database storage
    bom_id = hash(json.dumps(bom_json, sort_keys=True)) % 1000000
    
    return BOM(
        id=bom_id,
        project_id=project_id,
        bom_json=bom_json,
        created_at=datetime.utcnow()
    )

def mock_store_diff(engine, project_id, from_bom_id, to_bom_id, summary):
    """Mock diff storage for testing"""
    from core.schemas.models import BOMDiff
    
    diff_id = hash(f"{from_bom_id}-{to_bom_id}") % 1000000
    
    return BOMDiff(
        id=diff_id,
        project_id=project_id,
        from_bom=from_bom_id,
        to_bom=to_bom_id,
        summary=summary,
        created_at=datetime.utcnow()
    )

def test_full_integration():
    """Test full BOM → Diff → Policy workflow"""
    print("🚀 Testing Full BOM → Diff → Policy Integration")
    print("=" * 60)
    
    # Initialize engines
    bom_generator = BOMGenerator()
    diff_engine = DiffEngine()
    policy_engine = PolicyEngine()
    
    # Mock database operations
    bom_generator._store_bom = lambda pid, bj, bh: mock_store_bom(bom_generator, pid, bj, bh)
    diff_engine._store_diff = lambda pid, fid, tid, s: mock_store_diff(diff_engine, pid, fid, tid, s)
    
    # Step 1: Generate initial BOM (v1)
    print("\n📋 Step 1: Generate Initial BOM (v1)")
    print("-" * 40)
    
    state_v1 = create_initial_scan_state()
    state_v1 = bom_generator.generate_bom(state_v1)
    
    if state_v1.error:
        print(f"   ❌ BOM generation failed: {state_v1.error}")
        return False
    
    print(f"   ✅ Generated BOM v1 (ID: {state_v1.bom.id})")
    print(f"   📊 Components: {len(state_v1.bom.bom_json.get('components', []))}")
    
    # Step 2: Generate updated BOM (v2)
    print("\n📋 Step 2: Generate Updated BOM (v2)")
    print("-" * 40)
    
    state_v2 = create_updated_scan_state()
    state_v2 = bom_generator.generate_bom(state_v2)
    
    if state_v2.error:
        print(f"   ❌ BOM generation failed: {state_v2.error}")
        return False
    
    print(f"   ✅ Generated BOM v2 (ID: {state_v2.bom.id})")
    print(f"   📊 Components: {len(state_v2.bom.bom_json.get('components', []))}")
    
    # Step 3: Generate diff between v1 and v2
    print("\n🔄 Step 3: Generate BOM Diff")
    print("-" * 40)
    
    # Mock getting previous BOM
    diff_engine._get_previous_bom = lambda pid, cid: state_v1.bom
    
    state_v2 = diff_engine.generate_diff(state_v2)
    
    if state_v2.error:
        print(f"   ❌ Diff generation failed: {state_v2.error}")
        return False
    
    print(f"   ✅ Generated diff (ID: {state_v2.diff.id})")
    print(f"   📈 Total changes: {state_v2.diff.summary['stats']['total_changes']}")
    print(f"   ➕ Additions: {state_v2.diff.summary['stats']['additions']}")
    print(f"   ➖ Removals: {state_v2.diff.summary['stats']['removals']}")
    print(f"   🔄 Modifications: {state_v2.diff.summary['stats']['modifications']}")
    
    # Print detailed changes
    for change in state_v2.diff.summary.get('changes', [])[:5]:  # Show first 5
        print(f"      - {change['type']}: {change.get('component_name', 'N/A')} ({change.get('details', 'N/A')})")
    
    # Step 4: Evaluate policies
    print("\n🛡️  Step 4: Evaluate Policies")
    print("-" * 40)
    
    # Mock policy retrieval
    test_policies = [
        Policy(id=1, rule="missing_license", severity=Severity.HIGH, spec={}),
        Policy(id=2, rule="unapproved_license", severity=Severity.HIGH, 
               spec={"allowed_licenses": ["MIT", "Apache-2.0", "BSD-3-Clause"]}),
        Policy(id=3, rule="unknown_provider", severity=Severity.MEDIUM, spec={}),
        Policy(id=4, rule="model_bump_major", severity=Severity.MEDIUM, spec={}),
        Policy(id=5, rule="prompt_changed_protected_path", severity=Severity.HIGH,
               spec={"protected_paths": ["/prompts/", "/prod/"]})
    ]
    
    policy_engine._get_active_policies = lambda: test_policies
    policy_engine._get_policy_overrides = lambda pid: {}
    policy_engine._is_duplicate_event = lambda event: False
    policy_engine._store_policy_event = lambda event: event
    
    state_v2 = policy_engine.evaluate_policies(state_v2)
    
    if state_v2.error:
        print(f"   ❌ Policy evaluation failed: {state_v2.error}")
        return False
    
    print(f"   ✅ Evaluated policies")
    print(f"   🚨 Policy events: {len(state_v2.policy_events)}")
    
    # Group events by severity
    events_by_severity = {}
    for event in state_v2.policy_events:
        severity = event.severity.value
        events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
    
    for severity, count in events_by_severity.items():
        print(f"      - {severity.upper()}: {count} events")
    
    # Print detailed policy events
    print("\n   📋 Policy Event Details:")
    for event in state_v2.policy_events:
        print(f"      - [{event.severity.value.upper()}] {event.rule}: {event.details.get('message', 'N/A')}")
    
    # Step 5: Validate expected results
    print("\n✅ Step 5: Validate Results")
    print("-" * 40)
    
    success = True
    
    # Should have detected changes
    if state_v2.diff.summary['stats']['total_changes'] == 0:
        print("   ❌ No changes detected in diff")
        success = False
    else:
        print(f"   ✅ Detected {state_v2.diff.summary['stats']['total_changes']} changes")
    
    # Should have policy violations
    if len(state_v2.policy_events) == 0:
        print("   ❌ No policy violations detected")
        success = False
    else:
        print(f"   ✅ Detected {len(state_v2.policy_events)} policy violations")
    
    # Should have high severity events (missing license, unapproved license, prompt change)
    high_severity_events = [e for e in state_v2.policy_events if e.severity == Severity.HIGH]
    if len(high_severity_events) == 0:
        print("   ❌ No high severity policy events detected")
        success = False
    else:
        print(f"   ✅ Detected {len(high_severity_events)} high severity events")
    
    # Should have medium severity events (unknown provider, version bump)
    medium_severity_events = [e for e in state_v2.policy_events if e.severity == Severity.MEDIUM]
    if len(medium_severity_events) == 0:
        print("   ❌ No medium severity policy events detected")
        success = False
    else:
        print(f"   ✅ Detected {len(medium_severity_events)} medium severity events")
    
    return success

def main():
    """Run integration test"""
    print("🧪 ML-BOM Autopilot - Integration Test")
    print("Testing BOM Generation → Diff Analysis → Policy Evaluation")
    
    try:
        success = test_full_integration()
        
        if success:
            print("\n🎉 Integration test PASSED!")
            print("All components working together correctly.")
            return 0
        else:
            print("\n❌ Integration test FAILED!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())