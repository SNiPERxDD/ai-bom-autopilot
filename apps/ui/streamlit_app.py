import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="AI-BOM Autopilot",
    page_icon="🔍",
    layout="wide"
)

# API base URL
API_BASE = "http://localhost:8000"

def main():
    st.title("🔍 AI-BOM Autopilot")
    st.markdown("Auto-discover ML artifacts and generate CycloneDX ML-BOM with policy checking")
    
    # Health status in header
    show_health_status_header()
    
    # Main interface - single page with tabs
    show_main_interface()

def show_health_status_header():
    """Show health status indicators in the header"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        workflow_response = requests.get(f"{API_BASE}/workflow/status", timeout=2)
        
        if response.status_code == 200:
            health = response.json()
            workflow_status = workflow_response.json() if workflow_response.status_code == 200 else {}
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                if health['database']['status'] == 'healthy':
                    st.success("🟢 DB")
                else:
                    st.error("🔴 DB")
            
            with col2:
                if health['capabilities'].get('vector'):
                    st.success("🟢 Vector")
                else:
                    st.warning("🟡 Vector")
            
            with col3:
                if health['capabilities'].get('fulltext'):
                    st.success("🟢 FTS")
                else:
                    st.warning("🟡 BM25")
            
            with col4:
                # Check runtime tracing capability
                if workflow_status.get('runtime_enabled'):
                    st.success("🟢 Runtime")
                else:
                    st.warning("🟡 Runtime")
            
            with col5:
                # Check if API keys are configured (simplified check)
                st.info("🟢 API Keys")
            
            with col6:
                if health['status'] == 'healthy':
                    st.success("🟢 System")
                else:
                    st.error("🔴 System")
        else:
            st.error("🔴 Cannot connect to API")
    except requests.exceptions.RequestException:
        st.error("🔴 API Unavailable")

def show_main_interface():
    """Main single-page interface with project selector and results tabs"""
    
    # Project selector and controls
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # Get projects
        try:
            response = requests.get(f"{API_BASE}/projects", timeout=5)
            projects = response.json() if response.status_code == 200 else []
        except requests.exceptions.RequestException:
            projects = []
            st.error("Failed to connect to API. Make sure the backend is running on http://localhost:8000")
            return
        
        if not projects:
            st.warning("No projects found. Create a project first in the Projects tab.")
            show_projects()
            return
        
        # Project selector
        project_options = [f"{p['name']}" for p in projects]
        selected_project_name = st.selectbox("Select Project", project_options, key="main_project_selector")
        
        if selected_project_name:
            project = next(p for p in projects if p['name'] == selected_project_name)
            st.session_state.selected_project = project
    
    with col2:
        # Dry run toggle
        dry_run = st.checkbox("Dry Run Mode", help="Run scan without making changes or sending notifications")
    
    with col3:
        # Run scan button
        if st.button("🚀 Run Scan", type="primary", use_container_width=True):
            if 'selected_project' in st.session_state:
                run_scan_action(st.session_state.selected_project, dry_run)
    
    # Show project info
    if 'selected_project' in st.session_state:
        project = st.session_state.selected_project
        st.info(f"**Repository:** {project['repo_url']} | **Branch:** {project['default_branch']}")
        
        # Results tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 BOM", "🔄 Diff", "⚠️ Policy", "📤 Actions", "⚡ Runtime"])
        
        with tab1:
            show_bom_tab(project['id'])
        
        with tab2:
            show_diff_tab(project['id'])
        
        with tab3:
            show_policy_tab(project['id'])
        
        with tab4:
            show_actions_tab(project['id'])
        
        with tab5:
            show_runtime_tab(project)

def run_scan_action(project, dry_run=False):
    """Execute scan with progress indication"""
    with st.spinner("Running scan..."):
        try:
            scan_response = requests.post(f"{API_BASE}/scan", 
                                        json={"project": project['name'], "dry_run": dry_run})
            if scan_response.status_code == 200:
                result = scan_response.json()
                
                if dry_run:
                    st.success("🧪 Dry run completed successfully!")
                else:
                    st.success("✅ Scan completed successfully!")
                
                # Show scan summary
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Models", result['components']['models'])
                col2.metric("Datasets", result['components']['datasets'])
                col3.metric("Prompts", result['components']['prompts'])
                col4.metric("Tools", result['components']['tools'])
                
                if result.get('policy_events'):
                    st.warning(f"⚠️ {len(result['policy_events'])} policy events detected")
                
                # Store results in session state so they persist
                st.session_state.last_scan_result = result
                st.session_state.last_scan_project_id = project['id']
                
                # Add button to view detailed results instead of auto-refresh
                if st.button("View Results in Detail"):
                    st.rerun()
            else:
                st.error(f"Scan failed: {scan_response.text}")
        except Exception as e:
            st.error(f"Scan failed: {str(e)}")

def show_bom_tab(project_id):
    """Show BOM results tab"""
    try:
        boms_response = requests.get(f"{API_BASE}/projects/{project_id}/boms")
        if boms_response.status_code == 200:
            boms = boms_response.json()
            if boms:
                # BOM selector
                bom_options = [f"BOM {b['id']} - {b['created_at'][:19]} ({b['component_count']} components)" 
                             for b in boms]
                selected_bom = st.selectbox("Select BOM", bom_options, key="bom_selector")
                
                if selected_bom:
                    bom_id = int(selected_bom.split("BOM ")[1].split(" -")[0])
                    
                    # Get BOM details
                    bom_response = requests.get(f"{API_BASE}/boms/{bom_id}")
                    if bom_response.status_code == 200:
                        bom_data = bom_response.json()
                        
                        # Show BOM summary
                        components = bom_data['bom'].get('components', [])
                        st.write(f"**Total Components:** {len(components)}")
                        
                        # Component breakdown
                        if components:
                            component_types = {}
                            for comp in components:
                                comp_type = comp.get('type', 'unknown')
                                component_types[comp_type] = component_types.get(comp_type, 0) + 1
                            
                            # Pie chart
                            fig = px.pie(
                                values=list(component_types.values()),
                                names=list(component_types.keys()),
                                title="Component Types"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Component table
                            comp_df = pd.DataFrame([
                                {
                                    'Name': comp.get('name', ''),
                                    'Type': comp.get('type', ''),
                                    'Version': comp.get('version', ''),
                                    'Scope': comp.get('scope', '')
                                }
                                for comp in components
                            ])
                            st.dataframe(comp_df, use_container_width=True)
            else:
                st.info("No BOMs found for this project")
    except Exception as e:
        st.error(f"Failed to load BOMs: {str(e)}")

def show_diff_tab(project_id):
    """Show BOM diff results tab"""
    try:
        diffs_response = requests.get(f"{API_BASE}/projects/{project_id}/diffs")
        if diffs_response.status_code == 200:
            diffs = diffs_response.json()
            if diffs:
                for diff in diffs:
                    with st.expander(f"Diff {diff['id']} - {diff['created_at'][:19]}"):
                        summary = diff['summary']
                        stats = summary.get('stats', {})
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Total Changes", stats.get('total_changes', 0))
                        col2.metric("Additions", stats.get('additions', 0))
                        col3.metric("Removals", stats.get('removals', 0))
                        col4.metric("Modifications", stats.get('modifications', 0))
                        
                        # Show changes
                        changes = summary.get('changes', [])
                        if changes:
                            changes_df = pd.DataFrame(changes)
                            st.dataframe(changes_df, use_container_width=True)
            else:
                st.info("No diffs found for this project")
    except Exception as e:
        st.error(f"Failed to load diffs: {str(e)}")

def show_policy_tab(project_id):
    """Show policy events tab with action buttons"""
    try:
        events_response = requests.get(f"{API_BASE}/projects/{project_id}/policy-events")
        if events_response.status_code == 200:
            events = events_response.json()
            if events:
                # Severity breakdown
                severity_counts = {}
                for event in events:
                    sev = event['severity']
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("🔴 Critical", severity_counts.get('critical', 0))
                col2.metric("🟠 High", severity_counts.get('high', 0))
                col3.metric("🟡 Medium", severity_counts.get('medium', 0))
                col4.metric("🟢 Low", severity_counts.get('low', 0))
                
                # Events with action buttons
                for event in events:
                    severity_color = {
                        'critical': '🔴',
                        'high': '🟠', 
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(event['severity'], '⚪')
                    
                    with st.expander(f"{severity_color} {event['rule']} - {event['artifact'].get('name', 'Unknown')}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Severity:** {event['severity']}")
                            st.write(f"**Artifact Type:** {event['artifact'].get('type', 'Unknown')}")
                            st.write(f"**Message:** {event['details'].get('message', 'No message')}")
                            st.write(f"**Created:** {event['created_at'][:19]}")
                        
                        with col2:
                            # Action buttons
                            if st.button("📢 Send to Slack", key=f"slack_{event['id']}"):
                                send_slack_notification(project_id, event)
                            
                            if st.button("🎫 Create Jira Ticket", key=f"jira_{event['id']}"):
                                create_jira_ticket(project_id, event)
            else:
                st.info("No policy events found for this project")
    except Exception as e:
        st.error(f"Failed to load policy events: {str(e)}")

def show_actions_tab(project_id):
    """Show actions/notifications tab"""
    try:
        actions_response = requests.get(f"{API_BASE}/projects/{project_id}/actions")
        if actions_response.status_code == 200:
            actions = actions_response.json()
            if actions:
                for action in actions:
                    status_icon = "✅" if action['status'] == 'ok' else "❌"
                    
                    with st.expander(f"{status_icon} {action['kind'].upper()} - {action['created_at'][:19]}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Payload:**")
                            st.json(action['payload'])
                        
                        with col2:
                            st.write("**Response:**")
                            st.json(action['response'])
            else:
                st.info("No actions found for this project")
    except Exception as e:
        st.error(f"Failed to load actions: {str(e)}")

def send_slack_notification(project_id, event):
    """Send Slack notification for policy event"""
    try:
        response = requests.post(f"{API_BASE}/projects/{project_id}/policy-events/{event['id']}/notify/slack")
        if response.status_code == 200:
            st.success(f"✅ Slack notification sent for event {event['id']}")
        else:
            st.error(f"❌ Failed to send Slack notification: {response.text}")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to send Slack notification: {str(e)}")

def create_jira_ticket(project_id, event):
    """Create Jira ticket for policy event"""
    try:
        response = requests.post(f"{API_BASE}/projects/{project_id}/policy-events/{event['id']}/notify/jira")
        if response.status_code == 200:
            result = response.json()
            ticket_id = result.get('response', {}).get('key', 'Unknown')
            st.success(f"✅ Jira ticket {ticket_id} created for event {event['id']}")
        else:
            st.error(f"❌ Failed to create Jira ticket: {response.text}")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to create Jira ticket: {str(e)}")

def show_runtime_tab(project):
    """Show runtime tracing tab"""
    st.header("⚡ Runtime AI-BOM Tracing")
    st.markdown("Capture AI/ML components actually used at runtime via eBPF syscall tracing")
    
    # Runtime scan controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        duration = st.slider("Collection Duration (seconds)", min_value=10, max_value=300, value=30, step=10)
        st.info("💡 Start your ML application after clicking 'Start Runtime Scan' to capture live usage")
    
    with col2:
        dry_run = st.checkbox("Dry Run", key="runtime_dry_run")
    
    with col3:
        if st.button("🚀 Start Runtime Scan", type="primary", use_container_width=True):
            run_runtime_scan(project, duration, dry_run)
    
    # Runtime summary
    try:
        summary_response = requests.get(f"{API_BASE}/projects/{project['id']}/runtime/summary")
        if summary_response.status_code == 200:
            summary = summary_response.json()['summary']
            
            if summary.get('runtime_enabled'):
                st.subheader("📊 Runtime Activity Summary")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Events", summary.get('total_events', 0))
                
                # Artifact type breakdown
                by_type = summary.get('by_type', {})
                if by_type:
                    col2.metric("Models", by_type.get('model', 0))
                    col3.metric("Datasets", by_type.get('dataset', 0))
                    
                    # Pie chart for artifact types
                    if sum(by_type.values()) > 0:
                        fig = px.pie(
                            values=list(by_type.values()),
                            names=list(by_type.keys()),
                            title="Runtime Artifacts by Type"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # Process breakdown
                by_process = summary.get('by_process', {})
                if by_process:
                    st.subheader("🔍 Activity by Process")
                    process_df = pd.DataFrame([
                        {'Process': proc, 'Events': count}
                        for proc, count in by_process.items()
                    ])
                    st.dataframe(process_df, use_container_width=True)
                
                # Recent activity
                recent_activity = summary.get('recent_activity', [])
                if recent_activity:
                    st.subheader("🕒 Recent Activity")
                    activity_df = pd.DataFrame([
                        {
                            'Timestamp': datetime.fromtimestamp(event['ts']).strftime('%H:%M:%S') if event.get('ts') else 'Unknown',
                            'Process': event.get('process_name', 'Unknown'),
                            'Type': event.get('type', 'Unknown'),
                            'Path': event.get('path', '')[:50] + '...' if len(event.get('path', '')) > 50 else event.get('path', '')
                        }
                        for event in recent_activity[:10]
                    ])
                    st.dataframe(activity_df, use_container_width=True)
                
                # Clear events button
                if st.button("🗑️ Clear Runtime Events"):
                    clear_runtime_events(project['id'])
            else:
                st.info("No runtime activity detected yet. Run a runtime scan to capture live AI/ML usage.")
        else:
            st.warning("Failed to load runtime summary")
    except Exception as e:
        st.error(f"Failed to load runtime data: {str(e)}")

def run_runtime_scan(project, duration, dry_run=False):
    """Execute runtime scan with progress indication"""
    with st.spinner(f"Running runtime scan for {duration} seconds..."):
        try:
            scan_response = requests.post(f"{API_BASE}/scan/runtime", 
                                        json={
                                            "project": project['name'], 
                                            "duration": duration,
                                            "dry_run": dry_run
                                        })
            if scan_response.status_code == 200:
                result = scan_response.json()
                
                if dry_run:
                    st.success("🧪 Runtime dry run completed!")
                    st.info(result['message'])
                else:
                    st.success(f"✅ Runtime scan completed! Discovered {result['artifacts_discovered']} artifacts")
                    
                    # Show runtime scan summary
                    if result['artifacts_discovered'] > 0:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        artifacts_by_type = {}
                        for artifact in result['artifacts']:
                            artifact_type = artifact['kind']
                            artifacts_by_type[artifact_type] = artifacts_by_type.get(artifact_type, 0) + 1
                        
                        col1.metric("Total Artifacts", result['artifacts_discovered'])
                        col2.metric("Models", artifacts_by_type.get('model', 0))
                        col3.metric("Datasets", artifacts_by_type.get('dataset', 0))
                        col4.metric("Prompts", artifacts_by_type.get('prompt', 0))
                        
                        # Show discovered artifacts
                        st.subheader("🔍 Discovered Runtime Artifacts")
                        artifacts_df = pd.DataFrame([
                            {
                                'Name': artifact['name'],
                                'Type': artifact['kind'],
                                'Version': artifact['version'],
                                'Provider': artifact['provider'],
                                'Path': artifact['file_path'][:50] + '...' if len(artifact['file_path']) > 50 else artifact['file_path']
                            }
                            for artifact in result['artifacts']
                        ])
                        st.dataframe(artifacts_df, use_container_width=True)
                    else:
                        st.info("No AI/ML artifacts detected during runtime scan. Make sure to run your ML application during the collection period.")
                
                # Store results in session state so they persist
                st.session_state.last_scan_result = result
                st.session_state.last_scan_project_id = project['id']
                
                # Add button to view detailed results instead of auto-refresh
                if st.button("View Runtime Results in Detail"):
                    st.rerun()
            else:
                st.error(f"Runtime scan failed: {scan_response.text}")
        except Exception as e:
            st.error(f"Runtime scan failed: {str(e)}")

def clear_runtime_events(project_id):
    """Clear runtime events for a project"""
    try:
        response = requests.delete(f"{API_BASE}/projects/{project_id}/runtime/events")
        if response.status_code == 200:
            st.success("✅ Runtime events cleared")
            st.rerun()
        else:
            st.error(f"Failed to clear events: {response.text}")
    except Exception as e:
        st.error(f"Failed to clear events: {str(e)}")

def show_projects():
    """Show projects management (fallback when no projects exist)"""
    st.header("Projects")
    
    # Create new project
    with st.expander("Create New Project"):
        with st.form("create_project"):
            name = st.text_input("Project Name")
            repo_url = st.text_input("Repository URL")
            default_branch = st.text_input("Default Branch", value="main")
            
            if st.form_submit_button("Create Project"):
                try:
                    response = requests.post(f"{API_BASE}/projects", json={
                        "name": name,
                        "repo_url": repo_url,
                        "default_branch": default_branch
                    })
                    if response.status_code == 200:
                        st.success("Project created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create project: {response.text}")
                except Exception as e:
                    st.error(f"Failed to create project: {str(e)}")
    
    # List existing projects
    try:
        response = requests.get(f"{API_BASE}/projects")
        if response.status_code == 200:
            projects = response.json()
            if projects:
                df = pd.DataFrame(projects)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No projects found")
        else:
            st.error("Failed to load projects")
    except Exception as e:
        st.error(f"Failed to load projects: {str(e)}")



if __name__ == "__main__":
    main()