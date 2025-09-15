#!/usr/bin/env python3
"""
Demonstration of the ML-BOM Autopilot workflow
"""

import os
import sys
import json
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.schemas.models import Project
from core.graph.workflow import ml_bom_workflow

def demo_workflow_status():
    """Demonstrate workflow status reporting"""
    print("🔧 ML-BOM Autopilot Workflow Configuration")
    print("=" * 50)
    
    status = ml_bom_workflow.get_workflow_status()
    
    print(f"Dry Run Mode: {status['dry_run']}")
    print(f"Allowed Tools: {', '.join(status['allowed_tools'])}")
    print("\nNode Timeouts:")
    
    for node, timeout in status['node_timeouts'].items():
        print(f"  {node}: {timeout}s")
    
    print()

def demo_scan_plan():
    """Demonstrate the scan planning functionality"""
    print("📋 Scan Planning Demo")
    print("=" * 30)
    
    # Valid project
    project = Project(
        id=1,
        name="demo-project",
        repo_url="https://github.com/example/ml-project.git",
        default_branch="main"
    )
    
    from core.schemas.models import ScanState
    state = ScanState(project=project)
    
    print(f"Planning scan for project: {project.name}")
    result = ml_bom_workflow._scan_plan_node(state)
    
    if result.error:
        print(f"❌ Planning failed: {result.error}")
    else:
        print("✅ Planning successful!")
        print(f"  Workflow version: {result.meta.get('workflow_version')}")
        print(f"  Scan start time: {result.meta.get('scan_start_time')}")
        print(f"  Counters initialized: {list(result.meta.get('counters', {}).keys())}")
    
    print()

def demo_dry_run_scan():
    """Demonstrate a dry run scan"""
    print("🧪 Dry Run Scan Demo")
    print("=" * 25)
    
    project = Project(
        id=1,
        name="demo-project",
        repo_url="https://github.com/example/ml-project.git",
        default_branch="main"
    )
    
    print(f"Starting dry run scan for: {project.name}")
    print("This will execute the workflow without database writes or external notifications...")
    
    start_time = time.time()
    
    try:
        # Note: This will fail due to missing database/services, but demonstrates the flow
        result = ml_bom_workflow.run_scan(project, dry_run=True)
        duration = time.time() - start_time
        
        print(f"✅ Scan completed in {duration:.2f}s")
        print(f"  Project: {result.project.name}")
        print(f"  Dry run mode: {result.meta.get('dry_run', False)}")
        
        if hasattr(result, 'error') and result.error:
            print(f"  Note: {result.error}")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"⚠️  Scan encountered issues after {duration:.2f}s: {e}")
        print("  This is expected in demo mode without full infrastructure")
    
    print()

def demo_workflow_graph():
    """Show the workflow graph structure"""
    print("🔄 Workflow Graph Structure")
    print("=" * 35)
    
    print("Node Sequence:")
    nodes = [
        "scan_plan", "scan_git", "scan_hf", "normalize", 
        "embed_index", "generate_bom", "diff_previous", 
        "check_policies", "notify"
    ]
    
    for i, node in enumerate(nodes):
        if i == 0:
            print(f"  START → {node}")
        elif i == len(nodes) - 1:
            print(f"  {node} → END")
        else:
            print(f"  {node} → {nodes[i+1]}")
    
    print("\nFeatures:")
    print("  ✅ Timeout protection on all nodes")
    print("  ✅ Retry logic with exponential backoff")
    print("  ✅ Dry run mode support")
    print("  ✅ Tool allowlist enforcement")
    print("  ✅ Comprehensive error handling")
    print("  ✅ State management throughout workflow")
    
    print()

def main():
    """Run the workflow demonstration"""
    print("🤖 ML-BOM Autopilot Workflow Demo")
    print("=" * 40)
    print()
    
    demo_workflow_status()
    demo_scan_plan()
    demo_workflow_graph()
    demo_dry_run_scan()
    
    print("🎉 Demo completed!")
    print("\nTo use the workflow:")
    print("1. Start the FastAPI server: python -m apps.api.main")
    print("2. POST to /scan with: {\"project\": \"your-project\", \"dry_run\": true}")
    print("3. Check /workflow/status for configuration")

if __name__ == "__main__":
    main()