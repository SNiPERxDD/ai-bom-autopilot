#!/usr/bin/env python3
"""
Ship Readiness Verification for ML-BOM Autopilot
Comprehensive check to confirm the project is ready for production deployment
"""

import os
import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple

def check_project_structure() -> Tuple[bool, List[str]]:
    """Verify project follows industry-standard structure"""
    required_dirs = [
        'apps', 'apps/api', 'apps/ui',
        'core', 'core/bom', 'core/db', 'core/diff', 'core/embeddings',
        'core/graph', 'core/mcp_tools', 'core/normalize', 'core/policy',
        'core/scan_git', 'core/scan_hf', 'core/schemas', 'core/search',
        'tests', 'docs', 'examples', 'seed'
    ]
    
    required_files = [
        'README.md', 'requirements.txt', '.env.example', '.gitignore',
        'run.sh', 'demo_workflow.py', 'run_all_tests.py'
    ]
    
    issues = []
    
    # Check directories
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            issues.append(f"Missing directory: {dir_path}")
    
    # Check files
    for file_path in required_files:
        if not os.path.exists(file_path):
            issues.append(f"Missing file: {file_path}")
    
    return len(issues) == 0, issues

def check_core_imports() -> Tuple[bool, List[str]]:
    """Verify all core modules can be imported"""
    core_modules = [
        'core.schemas.models',
        'core.graph.workflow',
        'core.scan_git.scanner',
        'core.scan_hf.fetcher',
        'core.normalize.classifier',
        'core.embeddings.embedder',
        'core.bom.generator',
        'core.diff.engine',
        'core.policy.engine',
        'core.mcp_tools.slack',
        'core.mcp_tools.jira',
        'core.db.connection',
        'core.search.engine'
    ]
    
    issues = []
    
    for module_name in core_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            issues.append(f"Cannot import {module_name}: {e}")
        except Exception as e:
            issues.append(f"Error importing {module_name}: {e}")
    
    return len(issues) == 0, issues

def check_api_structure() -> Tuple[bool, List[str]]:
    """Verify API endpoints are properly defined"""
    try:
        from apps.api.main import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    if method != 'HEAD':  # Skip HEAD methods
                        routes.append(f"{method} {route.path}")
        
        required_endpoints = [
            'GET /health',
            'GET /projects',
            'POST /projects',
            'POST /scan',
            'GET /projects/{project_id}/boms',
            'GET /boms/{bom_id}',
            'GET /projects/{project_id}/diffs',
            'GET /projects/{project_id}/policy-events',
            'GET /projects/{project_id}/actions'
        ]
        
        issues = []
        for endpoint in required_endpoints:
            if endpoint not in routes:
                issues.append(f"Missing API endpoint: {endpoint}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Failed to check API structure: {e}"]

def check_workflow_completeness() -> Tuple[bool, List[str]]:
    """Verify LangGraph workflow is complete"""
    try:
        from core.graph.workflow import ml_bom_workflow
        
        # Check workflow status
        status = ml_bom_workflow.get_workflow_status()
        
        required_nodes = [
            'scan_plan', 'scan_git', 'scan_hf', 'normalize',
            'embed_index', 'generate_bom', 'diff_previous',
            'check_policies', 'notify'
        ]
        
        issues = []
        
        # Check node timeouts are configured
        node_timeouts = status.get('node_timeouts', {})
        for node in required_nodes:
            if node not in node_timeouts:
                issues.append(f"Missing timeout configuration for node: {node}")
        
        # Check allowed tools
        allowed_tools = status.get('allowed_tools', [])
        if 'slack' not in allowed_tools:
            issues.append("Slack not in allowed tools")
        if 'jira' not in allowed_tools:
            issues.append("Jira not in allowed tools")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Failed to check workflow: {e}"]

def check_database_schema() -> Tuple[bool, List[str]]:
    """Verify database schema is properly defined"""
    try:
        # Check if migrations file exists and has required functions
        migrations_file = 'core/db/migrations.py'
        if not os.path.exists(migrations_file):
            return False, ["Missing migrations file"]
        
        # Read migrations file to check for table definitions
        with open(migrations_file, 'r') as f:
            migrations_content = f.read()
        
        required_tables = [
            'projects', 'models', 'datasets', 'prompts', 'tools',
            'prompt_blobs', 'evidence_chunks', 'boms', 'bom_diffs',
            'policies', 'policy_overrides', 'policy_events',
            'suppressions', 'actions'
        ]
        
        issues = []
        
        # Check for table definitions in migrations
        migrations_upper = migrations_content.upper()
        for table in required_tables:
            if f'CREATE TABLE IF NOT EXISTS {table.upper()}' not in migrations_upper and f'CREATE TABLE {table.upper()}' not in migrations_upper:
                issues.append(f"Missing table definition: {table}")
        
        # Check for key migration functions
        required_functions = ['run_migrations', 'test_fulltext_support']
        for func in required_functions:
            if f'def {func}' not in migrations_content:
                issues.append(f"Missing migration function: {func}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Failed to check database schema: {e}"]

def check_ui_completeness() -> Tuple[bool, List[str]]:
    """Verify UI has all required components"""
    ui_file = 'apps/ui/streamlit_app.py'
    
    if not os.path.exists(ui_file):
        return False, ["Missing UI file: apps/ui/streamlit_app.py"]
    
    try:
        with open(ui_file, 'r') as f:
            ui_content = f.read()
        
        required_functions = [
            'show_health_status_header',
            'show_main_interface',
            'show_bom_tab',
            'show_diff_tab',
            'show_policy_tab',
            'show_actions_tab'
        ]
        
        issues = []
        for func in required_functions:
            if f"def {func}" not in ui_content:
                issues.append(f"Missing UI function: {func}")
        
        # Check for key UI elements
        ui_elements = [
            'st.selectbox',  # Project selector
            'st.button',     # Run scan button
            'st.tabs',       # Results tabs
            'st.checkbox'    # Dry run toggle
        ]
        
        for element in ui_elements:
            if element not in ui_content:
                issues.append(f"Missing UI element: {element}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Failed to check UI: {e}"]

def check_documentation_quality() -> Tuple[bool, List[str]]:
    """Verify documentation is comprehensive"""
    readme_file = 'README.md'
    
    if not os.path.exists(readme_file):
        return False, ["Missing main README.md"]
    
    try:
        with open(readme_file, 'r') as f:
            readme_content = f.read()
        
        required_sections = [
            '# 🔍 AI-BOM Autopilot',
            '## 🚀 Quick Start',
            '## 🏗️ Architecture Overview',
            '## ✨ Key Features',
            '## 🔧 Environment Setup',
            '## 📊 System Capabilities',
            '## 🧪 Testing & Validation',
            '## 📁 Project Structure'
        ]
        
        issues = []
        for section in required_sections:
            if section not in readme_content:
                issues.append(f"Missing README section: {section}")
        
        # Check for Mermaid diagrams
        if '```mermaid' not in readme_content:
            issues.append("Missing architecture diagrams")
        
        # Check README files in subdirectories
        subdirs_with_readme = ['apps', 'core', 'tests', 'docs', 'examples', 'seed']
        for subdir in subdirs_with_readme:
            readme_path = f"{subdir}/README.md"
            if not os.path.exists(readme_path):
                issues.append(f"Missing README in {subdir}/")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Failed to check documentation: {e}"]

def check_test_coverage() -> Tuple[bool, List[str]]:
    """Verify comprehensive test coverage"""
    test_dir = 'tests'
    
    if not os.path.exists(test_dir):
        return False, ["Missing tests directory"]
    
    test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
    
    required_test_categories = [
        'test_bom_generator.py',
        'test_diff_engine.py',
        'test_policy_engine.py',
        'test_embeddings.py',
        'test_hybrid_search.py',
        'test_slack_notifier.py',
        'test_jira_notifier.py',
        'test_e2e_mock.py',
        'test_workflow_integration.py'
    ]
    
    issues = []
    for test_file in required_test_categories:
        if test_file not in test_files:
            issues.append(f"Missing test file: {test_file}")
    
    # Check test runner
    if not os.path.exists('run_all_tests.py'):
        issues.append("Missing test runner: run_all_tests.py")
    
    return len(issues) == 0, issues

def check_configuration_completeness() -> Tuple[bool, List[str]]:
    """Verify configuration is complete"""
    env_example = '.env.example'
    
    if not os.path.exists(env_example):
        return False, ["Missing .env.example file"]
    
    try:
        with open(env_example, 'r') as f:
            env_content = f.read()
        
        required_vars = [
            'TIDB_URL', 'DB_USER', 'DB_PASS', 'DB_NAME',
            'EMBED_PROVIDER', 'OPENAI_API_KEY', 'EMBEDDING_DIM',
            'SLACK_WEBHOOK_URL', 'JIRA_URL', 'JIRA_USERNAME', 'JIRA_API_TOKEN'
        ]
        
        issues = []
        for var in required_vars:
            if var not in env_content:
                issues.append(f"Missing environment variable: {var}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Failed to check configuration: {e}"]

def run_ship_readiness_check():
    """Run comprehensive ship readiness verification"""
    print("🚀 ML-BOM Autopilot Ship Readiness Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Project Structure", check_project_structure),
        ("Core Imports", check_core_imports),
        ("API Structure", check_api_structure),
        ("Workflow Completeness", check_workflow_completeness),
        ("Database Schema", check_database_schema),
        ("UI Completeness", check_ui_completeness),
        ("Documentation Quality", check_documentation_quality),
        ("Test Coverage", check_test_coverage),
        ("Configuration Completeness", check_configuration_completeness)
    ]
    
    results = []
    total_issues = 0
    
    for check_name, check_func in checks:
        print(f"🔍 Checking {check_name}...")
        try:
            passed, issues = check_func()
            if passed:
                print(f"  ✅ PASS")
                results.append((check_name, True, []))
            else:
                print(f"  ❌ FAIL ({len(issues)} issues)")
                for issue in issues[:3]:  # Show first 3 issues
                    print(f"    • {issue}")
                if len(issues) > 3:
                    print(f"    • ... and {len(issues) - 3} more")
                results.append((check_name, False, issues))
                total_issues += len(issues)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append((check_name, False, [str(e)]))
            total_issues += 1
        print()
    
    # Summary
    print("=" * 60)
    print("📊 SHIP READINESS SUMMARY")
    print("=" * 60)
    
    passed_checks = sum(1 for _, passed, _ in results if passed)
    total_checks = len(results)
    
    print(f"📈 Results: {passed_checks}/{total_checks} checks passed")
    print(f"🚨 Total Issues: {total_issues}")
    print()
    
    print("📋 Detailed Results:")
    for check_name, passed, issues in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {check_name}")
    
    print()
    
    # Final assessment
    if passed_checks == total_checks:
        print("🎉 PROJECT IS READY TO SHIP! 🚀")
        print("All checks passed. The ML-BOM Autopilot is production-ready.")
        return True
    elif passed_checks >= total_checks * 0.8:  # 80% pass rate
        print("⚠️  PROJECT IS MOSTLY READY TO SHIP")
        print(f"Minor issues detected ({total_issues} total). Address these before deployment:")
        print()
        for check_name, passed, issues in results:
            if not passed:
                print(f"🔧 {check_name}:")
                for issue in issues:
                    print(f"  • {issue}")
        return False
    else:
        print("❌ PROJECT NOT READY TO SHIP")
        print("Significant issues detected. Please address before deployment.")
        return False

if __name__ == "__main__":
    # Change to project directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Add to Python path
    sys.path.insert(0, script_dir)
    
    success = run_ship_readiness_check()
    sys.exit(0 if success else 1)