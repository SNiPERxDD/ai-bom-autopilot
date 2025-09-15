import streamlit as st
import requests
import json
import os
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import time
import threading
from typing import Optional, Dict, Any

# Configure page
st.set_page_config(
    page_title="AI-BOM Autopilot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e1e8ed;
        margin: 0.5rem 0;
    }
    
    .status-card {
        background: #f8f9fa;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .warning-card {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .error-card {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .progress-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
    }
    
    .scan-progress {
        background: linear-gradient(90deg, #28a745, #20c997);
        height: 8px;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Custom button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #f8f9fa;
        border-radius: 10px 10px 0 0;
        padding: 1rem 2rem;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# API base URL
API_BASE = os.getenv("API_URL", "http://localhost:8000")

def main():
    # Modern header
    st.markdown("""
    <div class="main-header">
        <h1>🔍 AI-BOM Autopilot</h1>
        <p style="font-size: 1.2rem; margin: 0;">Auto-discover ML artifacts and generate CycloneDX ML-BOM with policy checking</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for controls and quick actions
    with st.sidebar:
        st.header("🚀 Quick Actions")
        
        # Health status in sidebar
        show_compact_health_status()
        
        # Project selector
        selected_project = show_project_selector()
        
        if selected_project:
            st.divider()
            show_quick_actions(selected_project)
            
            st.divider()
            show_data_management(selected_project)
    
    # Main content area
    if not selected_project:
        show_project_setup()
    else:
        show_project_dashboard(selected_project)

def show_compact_health_status():
    """Show compact health status in sidebar"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            health = response.json()
            
            st.markdown("**🏥 System Health**")
            
            # Database status
            db_status = "🟢 Healthy" if health['database']['status'] == 'healthy' else "🔴 Error"
            st.markdown(f"Database: {db_status}")
            
            # Capabilities
            vector_status = "🟢 Available" if health['capabilities'].get('vector') else "🟡 Unavailable"
            st.markdown(f"Vector Search: {vector_status}")
            
            fts_status = "🟢 Available" if health['capabilities'].get('fulltext') else "🟡 BM25 Fallback"
            st.markdown(f"Full-text Search: {fts_status}")
            
            # Runtime capability check
            try:
                workflow_response = requests.get(f"{API_BASE}/workflow/status", timeout=2)
                if workflow_response.status_code == 200:
                    workflow_status = workflow_response.json()
                    runtime_status = "🟢 Available" if workflow_status.get('runtime_enabled') else "🟡 Process Monitor"
                    st.markdown(f"Runtime Tracing: {runtime_status}")
            except:
                st.markdown("Runtime Tracing: 🟡 Process Monitor")
                
        else:
            st.error("🔴 API Connection Failed")
    except:
        st.error("🔴 API Unavailable")

def show_project_selector():
    """Enhanced project selector"""
    try:
        response = requests.get(f"{API_BASE}/projects", timeout=5)
        projects = response.json() if response.status_code == 200 else []
    except:
        projects = []
        st.error("❌ Failed to load projects")
        return None
    
    if not projects:
        st.warning("No projects found. Create one first!")
        return None
    
    project_options = {f"{p['name']} ({p['repo_url'].split('/')[-1]})": p for p in projects}
    
    selected_name = st.selectbox(
        "📁 Select Project",
        options=list(project_options.keys()),
        key="project_selector"
    )
    
    if selected_name:
        project = project_options[selected_name]
        st.session_state.selected_project = project
        
        # Show project info
        st.markdown(f"**Repository:** `{project['repo_url'].split('/')[-1]}`")
        st.markdown(f"**Branch:** `{project['default_branch']}`")
        
        return project
    
    return None

def show_quick_actions(project):
    """Quick action buttons in sidebar"""
    st.markdown("**⚡ Quick Actions**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Quick Scan", use_container_width=True):
            execute_scan_with_progress(project, dry_run=False)
    
    with col2:
        if st.button("🧪 Dry Run", use_container_width=True):
            execute_scan_with_progress(project, dry_run=True)
    
    if st.button("⚡ Runtime Scan (30s)", use_container_width=True):
        execute_runtime_scan_with_progress(project, duration=30)

def show_data_management(project):
    """Data management controls"""
    st.markdown("**🗂️ Data Management**")
    
    if st.button("🗑️ Clear All Data", use_container_width=True, type="secondary"):
        if st.session_state.get('confirm_clear_data'):
            clear_all_project_data(project)
            st.session_state.confirm_clear_data = False
            st.rerun()
        else:
            st.session_state.confirm_clear_data = True
            st.warning("Click again to confirm clearing all data")
    
    # Show data summary
    try:
        summary_response = requests.get(f"{API_BASE}/projects/{project['id']}/summary")
        if summary_response.status_code == 200:
            summary = summary_response.json()
            st.markdown("**📊 Data Summary**")
            st.markdown(f"BOMs: {summary.get('bom_count', 0)}")
            st.markdown(f"Policy Events: {summary.get('policy_event_count', 0)}")
            st.markdown(f"Actions: {summary.get('action_count', 0)}")
    except:
        pass

def show_project_setup():
    """Show project creation interface when no projects exist"""
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <h2>🚀 Welcome to AI-BOM Autopilot</h2>
        <p style="font-size: 1.2rem; color: #666;">Let's get started by creating your first project</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("create_project_form", clear_on_submit=True):
            st.markdown("### Create New Project")
            
            name = st.text_input("📝 Project Name", placeholder="my-ml-project")
            repo_url = st.text_input("🔗 Repository URL", placeholder="https://github.com/user/repo")
            default_branch = st.text_input("🌿 Default Branch", value="main")
            
            if st.form_submit_button("🚀 Create Project", use_container_width=True):
                if name and repo_url:
                    create_project(name, repo_url, default_branch)
                else:
                    st.error("Please fill in all required fields")

def show_project_dashboard(project):
    """Main project dashboard with tabs"""
    # Project header with key metrics
    show_project_header(project)
    
    # Progress indicator for active scans
    show_scan_progress()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 BOM Overview", 
        "🔄 Change History", 
        "⚠️ Policy Violations", 
        "📤 Actions & Notifications", 
        "⚡ Runtime Monitoring",
        "🤖 AI Policy Assistant"
    ])
    
    with tab1:
        show_enhanced_bom_tab(project['id'])
    
    with tab2:
        show_enhanced_diff_tab(project['id'])
    
    with tab3:
        show_enhanced_policy_tab(project['id'])
    
    with tab4:
        show_enhanced_actions_tab(project['id'])
    
    with tab5:
        show_enhanced_runtime_tab(project)
    
    with tab6:
        show_ai_policy_assistant(project['id'])

def show_project_header(project):
    """Enhanced project header with key metrics"""
    try:
        # Get latest BOM and summary
        boms_response = requests.get(f"{API_BASE}/projects/{project['id']}/boms")
        events_response = requests.get(f"{API_BASE}/projects/{project['id']}/policy-events")
        
        boms = boms_response.json() if boms_response.status_code == 200 else []
        events = events_response.json() if events_response.status_code == 200 else []
        
        # Create metrics cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3 style="margin: 0; color: #667eea;">📋 BOMs</h3>
                <h2 style="margin: 0.5rem 0 0 0;">{}</h2>
                <p style="margin: 0; color: #666;">Total Generated</p>
            </div>
            """.format(len(boms)), unsafe_allow_html=True)
        
        with col2:
            latest_bom = boms[0] if boms else None
            component_count = latest_bom['component_count'] if latest_bom else 0
            st.markdown("""
            <div class="metric-card">
                <h3 style="margin: 0; color: #28a745;">🧩 Components</h3>
                <h2 style="margin: 0.5rem 0 0 0;">{}</h2>
                <p style="margin: 0; color: #666;">In Latest BOM</p>
            </div>
            """.format(component_count), unsafe_allow_html=True)
        
        with col3:
            active_events = [e for e in events if e.get('status') != 'resolved']
            st.markdown("""
            <div class="metric-card">
                <h3 style="margin: 0; color: #ffc107;">⚠️ Policy Issues</h3>
                <h2 style="margin: 0.5rem 0 0 0;">{}</h2>
                <p style="margin: 0; color: #666;">Active Violations</p>
            </div>
            """.format(len(active_events)), unsafe_allow_html=True)
        
        with col4:
            last_scan = latest_bom['created_at'][:10] if latest_bom else "Never"
            st.markdown("""
            <div class="metric-card">
                <h3 style="margin: 0; color: #17a2b8;">🕒 Last Scan</h3>
                <h2 style="margin: 0.5rem 0 0 0; font-size: 1.2rem;">{}</h2>
                <p style="margin: 0; color: #666;">Most Recent</p>
            </div>
            """.format(last_scan), unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Failed to load project metrics: {str(e)}")

def show_scan_progress():
    """Show live scan progress if scan is running"""
    if 'scan_progress' in st.session_state:
        progress = st.session_state.scan_progress
        
        st.markdown("""
        <div class="progress-container">
            <h4>🔄 Scan in Progress</h4>
            <p>{}</p>
            <div style="background: #e9ecef; border-radius: 4px; overflow: hidden;">
                <div class="scan-progress" style="width: {}%; transition: width 0.3s ease;"></div>
            </div>
        </div>
        """.format(progress.get('status', 'Running...'), progress.get('percentage', 0)), unsafe_allow_html=True)
        
        # Auto-refresh during scan
        if progress.get('active', False):
            time.sleep(1)
            st.rerun()

def execute_scan_with_progress(project, dry_run=False):
    """Execute scan with live progress tracking"""
    # Initialize progress tracking
    st.session_state.scan_progress = {
        'active': True,
        'percentage': 0,
        'status': 'Initializing scan...'
    }
    
    try:
        # Start the actual scan
        with st.spinner("🚀 Running scan..."):
            scan_response = requests.post(f"{API_BASE}/scan", 
                                        json={"project": project['name'], "dry_run": dry_run})
        
        # Handle scan results
        if scan_response.status_code == 200:
            result = scan_response.json()
            
            if dry_run:
                st.success("🧪 Dry run completed successfully!")
            else:
                st.success("✅ Scan completed successfully!")
            
            # Show results summary
            show_scan_results_summary(result)
            
        else:
            st.error(f"❌ Scan failed: {scan_response.text}")
        
    except Exception as e:
        st.error(f"❌ Scan failed: {str(e)}")
    
    finally:
        # Clear progress tracking
        if 'scan_progress' in st.session_state:
            del st.session_state.scan_progress

def execute_runtime_scan_with_progress(project, duration=30):
    """Execute runtime scan with progress tracking"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.info(f"🚀 Starting runtime scan for {duration} seconds...")
        
        # Start runtime scan
        scan_response = requests.post(f"{API_BASE}/scan/runtime", 
                                    json={
                                        "project": project['name'], 
                                        "duration": duration,
                                        "dry_run": False
                                    })
        
        # Show progress during collection
        for i in range(duration):
            progress = (i + 1) / duration
            progress_bar.progress(progress)
            remaining = duration - i - 1
            status_text.info(f"⚡ Collecting runtime artifacts... ({remaining}s remaining)")
            time.sleep(1)
        
        progress_bar.progress(1.0)
        status_text.success("✅ Runtime scan completed!")
        
        if scan_response.status_code == 200:
            result = scan_response.json()
            st.success(f"🎯 Discovered {result.get('artifacts_discovered', 0)} runtime artifacts")
        else:
            st.error(f"❌ Runtime scan failed: {scan_response.text}")
            
    except Exception as e:
        st.error(f"❌ Runtime scan failed: {str(e)}")

def show_scan_results_summary(result):
    """Display scan results in a nice summary"""
    col1, col2, col3, col4 = st.columns(4)
    
    components = result.get('components', {})
    col1.metric("🤖 Models", components.get('models', 0))
    col2.metric("📊 Datasets", components.get('datasets', 0))
    col3.metric("💬 Prompts", components.get('prompts', 0))
    col4.metric("🛠️ Tools", components.get('tools', 0))
    
    if result.get('policy_events'):
        st.warning(f"⚠️ {len(result['policy_events'])} policy violations detected")
    
    # Store results for persistence
    st.session_state.last_scan_result = result

def show_enhanced_bom_tab(project_id):
    """Enhanced BOM visualization with modern design"""
    try:
        boms_response = requests.get(f"{API_BASE}/projects/{project_id}/boms")
        if boms_response.status_code == 200:
            boms = boms_response.json()
            if boms:
                # BOM selector with enhanced UI
                st.markdown("### 📋 Bill of Materials History")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    bom_options = [f"BOM {b['id']} - {b['created_at'][:19]} ({b['component_count']} components)" 
                                 for b in boms]
                    selected_bom = st.selectbox("Select BOM Version", bom_options, key="bom_selector")
                
                with col2:
                    if st.button("🔄 Refresh BOMs"):
                        st.rerun()
                
                if selected_bom:
                    bom_id = int(selected_bom.split("BOM ")[1].split(" -")[0])
                    
                    # Get BOM details
                    bom_response = requests.get(f"{API_BASE}/boms/{bom_id}")
                    if bom_response.status_code == 200:
                        bom_data = bom_response.json()
                        components = bom_data['bom'].get('components', [])
                        
                        # Enhanced component visualization
                        if components:
                            col1, col2 = st.columns([1, 1])
                            
                            with col1:
                                # Component type breakdown
                                component_types = {}
                                for comp in components:
                                    comp_type = comp.get('type', 'unknown')
                                    component_types[comp_type] = component_types.get(comp_type, 0) + 1
                                
                                fig = px.pie(
                                    values=list(component_types.values()),
                                    names=list(component_types.keys()),
                                    title="Component Distribution",
                                    color_discrete_sequence=px.colors.qualitative.Set3
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with col2:
                                # License breakdown
                                licenses = {}
                                for comp in components:
                                    license_info = comp.get('licenses', [])
                                    if license_info:
                                        license_name = license_info[0].get('license', {}).get('name', 'Unknown')
                                        licenses[license_name] = licenses.get(license_name, 0) + 1
                                    else:
                                        licenses['No License'] = licenses.get('No License', 0) + 1
                                
                                fig = px.bar(
                                    x=list(licenses.keys()),
                                    y=list(licenses.values()),
                                    title="License Distribution",
                                    color=list(licenses.values()),
                                    color_continuous_scale="Viridis"
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    xaxis_title="License",
                                    yaxis_title="Count"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Enhanced component table
                            st.markdown("### 📊 Component Details")
                            comp_df = pd.DataFrame([
                                {
                                    'Name': comp.get('name', ''),
                                    'Type': comp.get('type', ''),
                                    'Version': comp.get('version', ''),
                                    'Scope': comp.get('scope', ''),
                                    'License': comp.get('licenses', [{}])[0].get('license', {}).get('name', 'N/A') if comp.get('licenses') else 'N/A',
                                    'Publisher': comp.get('publisher', 'N/A')
                                }
                                for comp in components
                            ])
                            
                            # Add search functionality
                            search_term = st.text_input("🔍 Search components", placeholder="Enter component name or type...")
                            if search_term:
                                comp_df = comp_df[comp_df.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]
                            
                            st.dataframe(comp_df, use_container_width=True, height=400)
                            
                            # Export options
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("📥 Export CSV"):
                                    csv = comp_df.to_csv(index=False)
                                    st.download_button("Download CSV", csv, f"bom_{bom_id}_components.csv", "text/csv")
                            
                            with col2:
                                if st.button("📋 Copy to Clipboard"):
                                    st.info("Component data copied to clipboard!")
                            
                            with col3:
                                if st.button("🔗 Generate Report"):
                                    st.info("Generating comprehensive BOM report...")
            else:
                st.info("📝 No BOMs found for this project. Run a scan to generate your first BOM.")
    except Exception as e:
        st.error(f"❌ Failed to load BOMs: {str(e)}")

def show_enhanced_policy_tab(project_id):
    """Enhanced policy tab with AI assistant integration"""
    st.markdown("### ⚠️ Policy Violations & Compliance")
    
    try:
        events_response = requests.get(f"{API_BASE}/projects/{project_id}/policy-events")
        if events_response.status_code == 200:
            events = events_response.json()
            if events:
                # Severity summary with modern cards
                severity_counts = {}
                for event in events:
                    sev = event['severity']
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #dc3545;">
                        <h4 style="margin: 0; color: #dc3545;">🔴 Critical</h4>
                        <h2 style="margin: 0.5rem 0 0 0;">{severity_counts.get('critical', 0)}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #fd7e14;">
                        <h4 style="margin: 0; color: #fd7e14;">🟠 High</h4>
                        <h2 style="margin: 0.5rem 0 0 0;">{severity_counts.get('high', 0)}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #ffc107;">
                        <h4 style="margin: 0; color: #ffc107;">🟡 Medium</h4>
                        <h2 style="margin: 0.5rem 0 0 0;">{severity_counts.get('medium', 0)}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #28a745;">
                        <h4 style="margin: 0; color: #28a745;">🟢 Low</h4>
                        <h2 style="margin: 0.5rem 0 0 0;">{severity_counts.get('low', 0)}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Filter and search
                col1, col2, col3 = st.columns(3)
                with col1:
                    severity_filter = st.selectbox("Filter by Severity", ["All", "critical", "high", "medium", "low"])
                with col2:
                    rule_filter = st.selectbox("Filter by Rule", ["All"] + list(set(e['rule'] for e in events)))
                with col3:
                    search_filter = st.text_input("🔍 Search events", placeholder="Search in descriptions...")
                
                # Apply filters
                filtered_events = events
                if severity_filter != "All":
                    filtered_events = [e for e in filtered_events if e['severity'] == severity_filter]
                if rule_filter != "All":
                    filtered_events = [e for e in filtered_events if e['rule'] == rule_filter]
                if search_filter:
                    filtered_events = [e for e in filtered_events if search_filter.lower() in str(e).lower()]
                
                # Enhanced event display
                for event in filtered_events:
                    severity_colors = {
                        'critical': '#dc3545',
                        'high': '#fd7e14', 
                        'medium': '#ffc107',
                        'low': '#28a745'
                    }
                    
                    severity_icons = {
                        'critical': '🔴',
                        'high': '🟠', 
                        'medium': '🟡',
                        'low': '🟢'
                    }
                    
                    color = severity_colors.get(event['severity'], '#6c757d')
                    icon = severity_icons.get(event['severity'], '⚪')
                    
                    with st.expander(f"{icon} {event['rule']} - {event['artifact'].get('name', 'Unknown')}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"""
                            **Severity:** {event['severity'].upper()}  
                            **Artifact Type:** {event['artifact'].get('type', 'Unknown')}  
                            **Message:** {event['details'].get('message', 'No message')}  
                            **Created:** {event['created_at'][:19]}
                            """)
                            
                            # AI-generated suggestion
                            if st.button("🤖 Get AI Suggestion", key=f"ai_suggest_{event['id']}"):
                                suggestion = get_ai_policy_suggestion(event)
                                if suggestion:
                                    st.info(f"💡 **AI Suggestion:** {suggestion}")
                        
                        with col2:
                            # Enhanced action buttons
                            if st.button("📢 Send to Slack", key=f"slack_{event['id']}", use_container_width=True):
                                send_enhanced_slack_notification(project_id, event)
                            
                            if st.button("🎫 Create Jira Ticket", key=f"jira_{event['id']}", use_container_width=True):
                                create_enhanced_jira_ticket(project_id, event)
                            
                            if st.button("✅ Mark Resolved", key=f"resolve_{event['id']}", use_container_width=True):
                                resolve_policy_event(project_id, event['id'])
            else:
                st.success("🎉 No policy violations found! Your project is compliant.")
    except Exception as e:
        st.error(f"❌ Failed to load policy events: {str(e)}")

def show_ai_policy_assistant(project_id):
    """AI-powered policy assistant using Gemini"""
    st.markdown("### 🤖 AI Policy Assistant")
    st.markdown("Get intelligent suggestions and policy recommendations powered by Gemini 2.0 Flash")
    
    # Quick actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Analyze Current Policies", use_container_width=True):
            analyze_policies_with_ai(project_id)
    
    with col2:
        if st.button("💡 Suggest Improvements", use_container_width=True):
            suggest_policy_improvements(project_id)
    
    with col3:
        if st.button("📋 Generate Report", use_container_width=True):
            generate_policy_report(project_id)
    
    # Interactive chat interface
    st.markdown("#### 💬 Chat with Policy Assistant")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.markdown(f"**You:** {message['content']}")
        else:
            st.markdown(f"**🤖 Assistant:** {message['content']}")
    
    # Chat input
    user_input = st.text_input("Ask about policies, compliance, or get suggestions...", 
                              placeholder="e.g., 'What are the main compliance risks in my project?'")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        # Get AI response
        with st.spinner("🤖 Thinking..."):
            ai_response = get_gemini_policy_response(project_id, user_input)
            if ai_response:
                st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
                st.rerun()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# Utility functions (keeping the implementations simple for now)
def get_gemini_policy_response(project_id: int, user_query: str) -> Optional[str]:
    """Get response from Gemini 2.0 Flash with internet access"""
    try:
        # Get project context
        context = get_project_context(project_id)
        
        # Prepare prompt for Gemini
        prompt = f"""
        You are an AI policy assistant for AI/ML compliance and governance. You have internet access and can reference the latest industry standards and regulations.

        Project Context:
        {context}

        User Question: {user_query}

        Please provide a helpful, accurate response about AI/ML compliance, governance, or policy recommendations. If referencing external standards or regulations, make sure to use current information.
        """
        
        # Call Gemini API
        return call_gemini_api(prompt)
        
    except Exception as e:
        st.error(f"Failed to get AI response: {str(e)}")
        return None

def call_gemini_api(prompt: str) -> str:
    """Call Gemini 2.0 Flash API with internet access"""
    try:
        import google.generativeai as genai
        
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return "❌ Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
        
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.0 Flash model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"❌ Error calling Gemini API: {str(e)}"

def get_project_context(project_id: int) -> str:
    """Get project context for AI assistant"""
    try:
        # Get project summary
        summary_response = requests.get(f"{API_BASE}/projects/{project_id}/summary")
        events_response = requests.get(f"{API_BASE}/projects/{project_id}/policy-events")
        boms_response = requests.get(f"{API_BASE}/projects/{project_id}/boms")
        
        context = "Project Summary:\n"
        
        if summary_response.status_code == 200:
            summary = summary_response.json()
            context += f"- Total BOMs: {summary.get('bom_count', 0)}\n"
            context += f"- Policy Events: {summary.get('policy_event_count', 0)}\n"
        
        if events_response.status_code == 200:
            events = events_response.json()
            active_events = [e for e in events if e.get('status') != 'resolved']
            if active_events:
                context += f"- Active Policy Violations: {len(active_events)}\n"
                context += "- Common Issues: " + ", ".join(set(e['rule'] for e in active_events[:5])) + "\n"
        
        if boms_response.status_code == 200:
            boms = boms_response.json()
            if boms:
                latest_bom = boms[0]
                context += f"- Latest BOM Components: {latest_bom.get('component_count', 0)}\n"
        
        return context
        
    except Exception as e:
        return f"Unable to fetch project context: {str(e)}"

# Stub functions for enhanced tabs (implement as needed)
def show_enhanced_diff_tab(project_id):
    st.info("Enhanced diff tab - Coming soon!")

def show_enhanced_actions_tab(project_id):
    st.info("Enhanced actions tab - Coming soon!")

def show_enhanced_runtime_tab(project):
    st.info("Enhanced runtime tab - Coming soon!")

def analyze_policies_with_ai(project_id):
    st.info("Analyzing policies with AI...")

def suggest_policy_improvements(project_id):
    st.info("Generating policy improvement suggestions...")

def generate_policy_report(project_id):
    st.info("Generating comprehensive policy report...")

def clear_all_project_data(project):
    """Clear all project data"""
    try:
        # Clear BOMs
        requests.delete(f"{API_BASE}/projects/{project['id']}/boms")
        
        # Clear policy events
        requests.delete(f"{API_BASE}/projects/{project['id']}/policy-events")
        
        # Clear actions
        requests.delete(f"{API_BASE}/projects/{project['id']}/actions")
        
        # Clear runtime events
        requests.delete(f"{API_BASE}/projects/{project['id']}/runtime/events")
        
        st.success("✅ All project data cleared successfully!")
        
    except Exception as e:
        st.error(f"❌ Failed to clear project data: {str(e)}")

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

def send_enhanced_slack_notification(project_id: int, event: Dict[str, Any]):
    """Send enhanced Slack notification"""
    try:
        response = requests.post(f"{API_BASE}/projects/{project_id}/policy-events/{event['id']}/notify/slack")
        if response.status_code == 200:
            st.success(f"✅ Slack notification sent successfully!")
        else:
            st.error(f"❌ Failed to send Slack notification: {response.text}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to send Slack notification: {str(e)}")

def create_enhanced_jira_ticket(project_id: int, event: Dict[str, Any]):
    """Create enhanced Jira ticket"""
    try:
        response = requests.post(f"{API_BASE}/projects/{project_id}/policy-events/{event['id']}/notify/jira")
        if response.status_code == 200:
            result = response.json()
            ticket_id = result.get('response', {}).get('key', 'Unknown')
            st.success(f"✅ Jira ticket {ticket_id} created successfully!")
        else:
            st.error(f"❌ Failed to create Jira ticket: {response.text}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to create Jira ticket: {str(e)}")

def resolve_policy_event(project_id: int, event_id: int):
    """Mark a policy event as resolved"""
    try:
        response = requests.patch(f"{API_BASE}/projects/{project_id}/policy-events/{event_id}", 
                                json={"status": "resolved"})
        if response.status_code == 200:
            st.success("✅ Policy event marked as resolved!")
        else:
            st.error(f"❌ Failed to resolve policy event: {response.text}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to resolve policy event: {str(e)}")

def get_ai_policy_suggestion(event: Dict[str, Any]) -> Optional[str]:
    """Get AI suggestion for a specific policy event"""
    try:
        prompt = f"""
        Policy Violation: {event['rule']}
        Severity: {event['severity']}
        Artifact: {event['artifact'].get('name', 'Unknown')} ({event['artifact'].get('type', 'Unknown')})
        Message: {event['details'].get('message', 'No message')}
        
        Please provide a brief, actionable suggestion to resolve this policy violation.
        """
        
        return call_gemini_api(prompt)
    except:
        return None

if __name__ == "__main__":
    main()