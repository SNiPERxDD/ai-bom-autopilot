#!/usr/bin/env python3

"""
Simplified Streamlit UI demo for AI-BOM Autopilot
This demonstrates the core functionality without requiring full workflow setup.
"""

import streamlit as st
import json
import sys
from pathlib import Path
import subprocess
import tempfile
import os

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our test scanning functionality
from test_scan import clone_and_scan_repository, generate_simple_bom

# Configure page
st.set_page_config(
    page_title="AI-BOM Autopilot Demo",
    page_icon="🔍",
    layout="wide"
)

def main():
    st.title("🔍 AI-BOM Autopilot Demo")
    st.markdown("Auto-discover ML artifacts and generate CycloneDX ML-BOM")
    
    # Show status indicators
    show_system_status()
    
    # Repository input and scan
    st.header("Repository Scanner")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        repo_url = st.text_input(
            "Repository URL", 
            value="https://github.com/SNiPERxDD/dual-model-music-emotion",
            help="Enter a GitHub repository URL to scan for ML/AI artifacts"
        )
    
    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        if st.button("🚀 Scan Repository", type="primary"):
            if repo_url:
                run_scan(repo_url)
    
    # Show results if available
    if 'scan_results' in st.session_state:
        show_scan_results()

def show_system_status():
    """Show system status indicators"""
    st.subheader("System Status")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.success("🟢 Database")
    
    with col2:
        st.success("🟢 Vector Search")
    
    with col3:
        st.warning("🟡 FTS (BM25 Fallback)")
    
    with col4:
        st.info("🟢 Scanning")
    
    with col5:
        st.success("🟢 BOM Generation")

def run_scan(repo_url):
    """Run repository scan"""
    with st.spinner("Scanning repository..."):
        try:
            # Run the scan
            artifacts = clone_and_scan_repository(repo_url)
            
            if artifacts:
                # Generate BOM
                bom = generate_simple_bom(artifacts, repo_url)
                
                # Store results
                st.session_state.scan_results = {
                    'repo_url': repo_url,
                    'artifacts': artifacts,
                    'bom': bom,
                    'total_count': len(artifacts)
                }
                
                st.success(f"✅ Scan completed! Found {len(artifacts)} artifacts")
                st.rerun()
            else:
                st.error("❌ No artifacts found in repository")
                
        except Exception as e:
            st.error(f"❌ Scan failed: {str(e)}")

def show_scan_results():
    """Display scan results in tabs"""
    results = st.session_state.scan_results
    
    st.header("Scan Results")
    st.info(f"**Repository:** {results['repo_url']}")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    models = [a for a in results['artifacts'] if a['type'] == 'model']
    datasets = [a for a in results['artifacts'] if a['type'] == 'dataset']
    code_files = [a for a in results['artifacts'] if a['type'] == 'code']
    
    col1.metric("Total Artifacts", results['total_count'])
    col2.metric("Models", len(models))
    col3.metric("Datasets", len(datasets))
    col4.metric("Code Files", len(code_files))
    
    # Results tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 BOM", "🔍 Artifacts", "📊 Analysis", "💾 Export"])
    
    with tab1:
        show_bom_tab(results['bom'])
    
    with tab2:
        show_artifacts_tab(results['artifacts'])
    
    with tab3:
        show_analysis_tab(results['artifacts'])
    
    with tab4:
        show_export_tab(results)

def show_bom_tab(bom):
    """Show BOM details"""
    st.subheader("CycloneDX ML-BOM")
    
    # BOM metadata
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Format:** {bom['bomFormat']}")
        st.write(f"**Spec Version:** {bom['specVersion']}")
    with col2:
        st.write(f"**Components:** {len(bom['components'])}")
        st.write(f"**Application:** {bom['metadata']['component']['name']}")
    
    # Components table
    st.subheader("Components")
    
    if bom['components']:
        # Create a more readable components table
        components_data = []
        for comp in bom['components']:
            size_mb = next((p['value'] for p in comp.get('properties', []) if p['name'] == 'size_mb'), '0')
            path = next((p['value'] for p in comp.get('properties', []) if p['name'] == 'path'), '')
            
            components_data.append({
                'Name': comp['name'],
                'Type': comp['type'],
                'Description': comp.get('description', ''),
                'Size (MB)': f"{float(size_mb):.1f}" if size_mb != '0' else 'N/A',
                'Path': path
            })
        
        st.dataframe(components_data, use_container_width=True)
    else:
        st.info("No components found")

def show_artifacts_tab(artifacts):
    """Show detailed artifacts"""
    st.subheader("Discovered Artifacts")
    
    # Group by type
    by_type = {}
    for artifact in artifacts:
        artifact_type = artifact['type']
        if artifact_type not in by_type:
            by_type[artifact_type] = []
        by_type[artifact_type].append(artifact)
    
    for artifact_type, items in by_type.items():
        with st.expander(f"{artifact_type.upper()} ({len(items)} found)"):
            for item in items:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**{item['name']}**")
                    st.write(f"📁 {item['path']}")
                    if item.get('description'):
                        st.write(f"ℹ️ {item['description']}")
                with col2:
                    if item.get('size_mb'):
                        st.metric("Size", f"{item['size_mb']:.1f} MB")

def show_analysis_tab(artifacts):
    """Show analysis of artifacts"""
    st.subheader("Analysis")
    
    # ML Libraries used
    all_libraries = set()
    for artifact in artifacts:
        if artifact['type'] == 'code' and artifact.get('libraries'):
            all_libraries.update(artifact['libraries'])
    
    if all_libraries:
        st.subheader("ML Libraries Detected")
        library_cols = st.columns(min(len(all_libraries), 4))
        for i, lib in enumerate(sorted(all_libraries)):
            with library_cols[i % len(library_cols)]:
                st.success(f"✅ {lib}")
    
    # File size distribution
    st.subheader("File Size Distribution")
    models = [a for a in artifacts if a['type'] == 'model' and a.get('size_mb')]
    if models:
        model_data = [(m['name'], m['size_mb']) for m in models]
        st.bar_chart({name: size for name, size in model_data})
    
    # Model types
    st.subheader("Model Types")
    model_types = {}
    for artifact in artifacts:
        if artifact['type'] == 'model':
            desc = artifact.get('description', 'Unknown')
            model_types[desc] = model_types.get(desc, 0) + 1
    
    if model_types:
        for model_type, count in model_types.items():
            st.write(f"• {model_type}: {count}")

def show_export_tab(results):
    """Show export options"""
    st.subheader("Export Results")
    
    # JSON download
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Download BOM")
        bom_json = json.dumps(results['bom'], indent=2)
        st.download_button(
            label="📥 Download CycloneDX BOM (JSON)",
            data=bom_json,
            file_name="ai_bom.json",
            mime="application/json"
        )
    
    with col2:
        st.subheader("Download Full Report")
        report = {
            'repository': results['repo_url'],
            'scan_summary': {
                'total_artifacts': results['total_count'],
                'models': len([a for a in results['artifacts'] if a['type'] == 'model']),
                'datasets': len([a for a in results['artifacts'] if a['type'] == 'dataset']),
                'code_files': len([a for a in results['artifacts'] if a['type'] == 'code'])
            },
            'artifacts': results['artifacts'],
            'bom': results['bom']
        }
        report_json = json.dumps(report, indent=2)
        st.download_button(
            label="📥 Download Full Report (JSON)",
            data=report_json,
            file_name="ai_scan_report.json",
            mime="application/json"
        )
    
    # Policy simulation
    st.subheader("Policy Check Simulation")
    st.info("✅ All models have valid formats")
    st.info("⚠️ 1 model lacks license information")
    st.info("✅ No unapproved model sources detected")

if __name__ == "__main__":
    main()