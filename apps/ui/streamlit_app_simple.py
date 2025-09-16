import streamlit as st
import requests
import json
import os
import pandas as pd
from typing import Optional, Dict, Any

# Configure page - minimalist setup
st.set_page_config(
    page_title="AI-BOM Autopilot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clean, minimal CSS
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    header[data-testid="stHeader"] {display: none;}
    
    /* Clean layout */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        max-width: 1200px;
    }
    
    /* Status indicators */
    .status-healthy { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-error { color: #dc3545; }
    
    /* Clean cards */
    .metric-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# API base URL
API_BASE = os.getenv("API_URL", "http://localhost:8000")

def main():
    # Simple header
    st.title("🔍 AI-BOM Autopilot")
    st.caption("Generate ML-BOM, track changes, enforce policies")
    
    # Health status and project selector in one row
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        show_health_status()
    
    with col2:
        selected_project = show_project_selector()
    
    with col3:
        if selected_project:
            show_quick_actions(selected_project)
    
    # Main content based on project selection
    if selected_project:
        show_project_content(selected_project)
    else:
        show_welcome_screen()

def show_health_status():
    """Compact health status display"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            health = response.json()
            
            # Simple status indicators
            db_icon = "🟢" if health['database']['status'] == 'healthy' else "🔴"
            vector_icon = "🟢" if health['capabilities'].get('vector') else "🟡"
            fts_icon = "🟢" if health['capabilities'].get('fulltext') else "🟡"
            
            st.markdown(f"""
            **System Status**  
            {db_icon} Database  
            {vector_icon} Vector Search  
            {fts_icon} Full-text Search  
            """)
        else:
            st.error("🔴 API Connection Failed")
    except:
        st.error("🔴 API Unavailable")

def show_project_selector():
    """Simple project selector with add option"""
    try:
        response = requests.get(f"{API_BASE}/projects", timeout=5)
        projects = response.json() if response.status_code == 200 else []
    except:
        projects = []
        st.error("Failed to load projects")
        return None
    
    # Create options with "Add New Project" at the end
    project_options = ["Select a project..."] + [p['name'] for p in projects] + ["➕ Add New Project"]
    
    selected = st.selectbox(
        "Project",
        options=project_options,
        key="project_selector"
    )
    
    if selected == "➕ Add New Project":
        show_add_project_modal()
        return None
    elif selected == "Select a project...":
        return None
    else:
        # Return the selected project
        return next((p for p in projects if p['name'] == selected), None)

def show_add_project_modal():
    """Inline project creation"""
    st.markdown("**Create New Project**")
    
    with st.form("create_project", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Project Name", placeholder="my-ml-project")
            repo_url = st.text_input("Repository URL", placeholder="https://github.com/user/repo")
        with col2:
            default_branch = st.text_input("Default Branch", value="main")
            
        if st.form_submit_button("Create Project"):
            if name and repo_url:
                create_project(name, repo_url, default_branch)
            else:
                st.error("Please provide project name and repository URL")

def show_quick_actions(project):
    """Essential action buttons"""
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Scan", type="primary", use_container_width=True):
            run_scan(project, dry_run=False)
    
    with col2:
        if st.button("🧪 Dry Run", use_container_width=True):
            run_scan(project, dry_run=True)

def show_project_content(project):
    """Main content area for selected project"""
    st.divider()
    
    # Project info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Project", project['name'])
    with col2:
        st.metric("Repository", project['repo_url'].split('/')[-1])
    with col3:
        st.metric("Branch", project['default_branch'])
    
    # Tabs for results
    tab1, tab2, tab3, tab4 = st.tabs(["📋 BOMs", "🔄 Changes", "⚠️ Policies", "📤 Actions"])
    
    with tab1:
        show_bom_results(project['id'])
    
    with tab2:
        show_diff_results(project['id'])
    
    with tab3:
        show_policy_results(project['id'])
    
    with tab4:
        show_action_results(project['id'])

def show_welcome_screen():
    """Welcome screen when no project selected"""
    st.markdown("""
    ### Welcome to AI-BOM Autopilot
    
    **Features:**
    - 🔍 **Auto-discover** ML artifacts in repositories
    - 📋 **Generate** standards-compliant CycloneDX ML-BOMs
    - 🔄 **Track changes** between scans
    - ⚠️ **Enforce policies** for compliance
    - 📤 **Send notifications** to Slack/Jira
    
    **Get Started:**
    1. Select a project from the dropdown above
    2. Or create a new project by selecting "➕ Add New Project"
    3. Run a scan to generate your first ML-BOM
    """)

def show_bom_results(project_id):
    """Display BOM results in simple format"""
    try:
        response = requests.get(f"{API_BASE}/projects/{project_id}/boms")
        if response.status_code == 200:
            boms = response.json()
            if boms:
                # Show latest BOM
                latest_bom = boms[0]
                st.metric("Latest BOM", f"ID {latest_bom['id']}", f"{latest_bom['component_count']} components")
                
                # Get BOM details
                bom_response = requests.get(f"{API_BASE}/boms/{latest_bom['id']}")
                if bom_response.status_code == 200:
                    bom_data = bom_response.json()
                    components = bom_data['bom'].get('components', [])
                    
                    if components:
                        # Simple component table
                        comp_df = pd.DataFrame([
                            {
                                'Name': comp.get('name', ''),
                                'Type': comp.get('type', ''),
                                'Version': comp.get('version', ''),
                                'License': comp.get('licenses', [{}])[0].get('license', {}).get('name', 'N/A') if comp.get('licenses') else 'N/A'
                            }
                            for comp in components
                        ])
                        st.dataframe(comp_df, use_container_width=True)
                    else:
                        st.info("No components found in this BOM")
            else:
                st.info("No BOMs found. Run a scan to generate your first BOM.")
    except Exception as e:
        st.error(f"Failed to load BOMs: {str(e)}")

def show_diff_results(project_id):
    """Display diff results"""
    try:
        response = requests.get(f"{API_BASE}/projects/{project_id}/diffs")
        if response.status_code == 200:
            diffs = response.json()
            if diffs:
                for diff in diffs[:3]:  # Show recent diffs
                    with st.expander(f"Diff {diff['id']} - {diff['created_at'][:19]}"):
                        summary = diff.get('summary', {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Added", summary.get('added', 0))
                        with col2:
                            st.metric("Modified", summary.get('modified', 0))
                        with col3:
                            st.metric("Removed", summary.get('removed', 0))
            else:
                st.info("No diffs found. Run multiple scans to see changes.")
    except Exception as e:
        st.error(f"Failed to load diffs: {str(e)}")

def show_policy_results(project_id):
    """Display policy violations"""
    try:
        response = requests.get(f"{API_BASE}/projects/{project_id}/policy-events")
        if response.status_code == 200:
            events = response.json()
            if events:
                # Group by severity
                high_events = [e for e in events if e['severity'] == 'high']
                medium_events = [e for e in events if e['severity'] == 'medium']
                low_events = [e for e in events if e['severity'] == 'low']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🔴 High", len(high_events))
                with col2:
                    st.metric("🟡 Medium", len(medium_events))
                with col3:
                    st.metric("🟢 Low", len(low_events))
                
                # Show recent violations
                for event in events[:5]:
                    severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(event['severity'], "⚪")
                    with st.expander(f"{severity_color} {event['rule']} - {event['artifact'].get('name', 'Unknown')}"):
                        st.write(f"**Message:** {event['details'].get('message', 'No message')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📢 Send to Slack", key=f"slack_{event['id']}"):
                                send_slack_notification(project_id, event['id'])
                        with col2:
                            if st.button("🎫 Create Jira Ticket", key=f"jira_{event['id']}"):
                                create_jira_ticket(project_id, event['id'])
            else:
                st.success("🎉 No policy violations found!")
    except Exception as e:
        st.error(f"Failed to load policy events: {str(e)}")

def show_action_results(project_id):
    """Display action history"""
    try:
        response = requests.get(f"{API_BASE}/projects/{project_id}/actions")
        if response.status_code == 200:
            actions = response.json()
            if actions:
                for action in actions[:5]:  # Show recent actions
                    status_icon = "✅" if action['status'] == 'ok' else "❌"
                    with st.expander(f"{status_icon} {action['kind'].upper()} - {action['created_at'][:19]}"):
                        st.json(action['payload'])
            else:
                st.info("No actions found")
    except Exception as e:
        st.error(f"Failed to load actions: {str(e)}")

def run_scan(project, dry_run=False):
    """Execute a scan"""
    mode = "dry run" if dry_run else "scan"
    try:
        with st.spinner(f"Running {mode}..."):
            response = requests.post(f"{API_BASE}/scan", 
                                   json={"project": project['name'], "dry_run": dry_run})
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ {mode.title()} completed successfully!")
            
            # Show quick results
            components = result.get('components', {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Models", components.get('models', 0))
            with col2:
                st.metric("Datasets", components.get('datasets', 0))
            with col3:
                st.metric("Prompts", components.get('prompts', 0))
                
            if result.get('policy_events'):
                st.warning(f"⚠️ {len(result['policy_events'])} policy violations detected")
                
            st.rerun()
        else:
            st.error(f"❌ {mode.title()} failed: {response.text}")
    except Exception as e:
        st.error(f"❌ {mode.title()} failed: {str(e)}")

def create_project(name: str, repo_url: str, default_branch: str):
    """Create a new project"""
    try:
        response = requests.post(f"{API_BASE}/projects", json={
            "name": name,
            "repo_url": repo_url,
            "default_branch": default_branch
        })
        if response.status_code == 200:
            st.success("✅ Project created successfully!")
            st.rerun()
        else:
            st.error(f"❌ Failed to create project: {response.text}")
    except Exception as e:
        st.error(f"❌ Failed to create project: {str(e)}")

def send_slack_notification(project_id: int, event_id: int):
    """Send Slack notification"""
    try:
        response = requests.post(f"{API_BASE}/projects/{project_id}/policy-events/{event_id}/notify/slack")
        if response.status_code == 200:
            st.success("✅ Slack notification sent!")
        else:
            st.error("❌ Failed to send Slack notification")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def create_jira_ticket(project_id: int, event_id: int):
    """Create Jira ticket"""
    try:
        response = requests.post(f"{API_BASE}/projects/{project_id}/policy-events/{event_id}/notify/jira")
        if response.status_code == 200:
            result = response.json()
            ticket_id = result.get('response', {}).get('key', 'Unknown')
            st.success(f"✅ Jira ticket {ticket_id} created!")
        else:
            st.error("❌ Failed to create Jira ticket")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()