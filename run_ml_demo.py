#!/usr/bin/env python3
"""
This script demonstrates how to run the AI-BOM Autopilot to detect ML/DL models.
It will:
1. Start the AI-BOM Autopilot services
2. Run the example_runtime_ml_app.py to generate ML activity
3. Launch the scan monitor to see real-time progress
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run AI-BOM Autopilot with ML app demonstration")
    parser.add_argument("--repo", type=str, default=None, help="Optional Git repository URL to scan")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run the scan in seconds")
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.absolute()
    
    # Step 1: Start the Autopilot services if not running
    print("🚀 Checking if AI-BOM Autopilot services are running...")
    try:
        # Check if API is running
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ AI-BOM Autopilot services are already running")
        else:
            print("❌ API is not responding correctly. Please start services with ./run.sh")
            return 1
    except Exception:
        print("🔄 Starting AI-BOM Autopilot services...")
        run_script = script_dir / "run.sh"
        if not run_script.exists():
            print(f"❌ Could not find run.sh at {run_script}")
            return 1
        
        # Start services in background
        subprocess.Popen(["bash", str(run_script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for services to start
        print("⏳ Waiting for services to start (this may take a minute)...")
        attempts = 0
        while attempts < 30:
            try:
                response = requests.get("http://localhost:8000/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Services are running")
                    break
            except Exception:
                pass
            attempts += 1
            time.sleep(2)
        
        if attempts >= 30:
            print("❌ Services failed to start within timeout period")
            return 1
    
    # Step 2: Create or select a project
    project_id = None
    project_name = "ML-Demo-Project"
    
    try:
        # Try to find existing project
        response = requests.get("http://localhost:8000/projects", timeout=5)
        projects = response.json() if response.status_code == 200 else []
        
        for project in projects:
            if project["name"] == project_name:
                project_id = project["id"]
                print(f"✅ Found existing project: {project_name} (ID: {project_id})")
                break
        
        if not project_id:
            # Create new project
            repo_url = args.repo or "https://github.com/example/ml-demo.git"
            payload = {
                "name": project_name,
                "repo_url": repo_url,
                "default_branch": "main"
            }
            response = requests.post("http://localhost:8000/projects", json=payload, timeout=5)
            if response.status_code == 200:
                project_id = response.json()["id"]
                print(f"✅ Created new project: {project_name} (ID: {project_id})")
            else:
                print(f"❌ Failed to create project: {response.text}")
                return 1
    except Exception as e:
        print(f"❌ Error working with projects: {e}")
        return 1
    
    # Step 3: Run the example ML app in a separate terminal window
    print("🤖 Starting example ML app...")
    example_app = script_dir / "examples" / "example_runtime_ml_app.py"
    if not example_app.exists():
        print(f"❌ Could not find example app at {example_app}")
        return 1
    
    ml_app_process = subprocess.Popen(
        ["python", str(example_app)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Step 4: Start a runtime scan
    print(f"🔍 Starting runtime scan for project {project_id}...")
    payload = {
        "project": str(project_id),
        "duration": args.duration,
        "dry_run": False
    }
    
    try:
        response = requests.post("http://localhost:8000/scan/runtime", json=payload, timeout=5)
        if response.status_code != 200:
            print(f"❌ Failed to start scan: {response.text}")
            return 1
        scan_id = response.json().get("scan_id")
        print(f"✅ Runtime scan started with ID: {scan_id}")
    except Exception as e:
        print(f"❌ Error starting scan: {e}")
        return 1
    
    # Step 5: Start the scan monitor
    print("📊 Starting scan monitor...")
    monitor_script = script_dir / "monitor_scan.py"
    if not monitor_script.exists():
        print(f"❌ Could not find monitor script at {monitor_script}")
        return 1
    
    try:
        # Run the monitor in the current terminal
        print("\n")
        monitor_process = subprocess.run(["python", str(monitor_script)])
        
        # Wait for ML app to finish
        ml_app_process.wait(timeout=args.duration + 10)
        
    except KeyboardInterrupt:
        print("\n🛑 Monitoring interrupted")
    finally:
        # Make sure ML app is terminated
        if ml_app_process.poll() is None:
            ml_app_process.terminate()
    
    # Step 6: Open the UI
    print("\n🌐 Scan complete! Opening UI to view results...")
    import webbrowser
    webbrowser.open(f"http://localhost:8501")
    
    print("\n✅ Done! View the scan results in the browser.")
    print("📝 Tips:")
    print("  - Check the 'Runtime' tab to see detected ML models")
    print("  - For ML/DL model detection, look at the 'Artifacts' section")
    print("  - Results will remain visible until you clear them")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
