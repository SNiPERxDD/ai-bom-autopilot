#!/usr/bin/env python3
"""
Progress Monitor for AI-BOM Autopilot.
Shows real-time scan progress by monitoring logs.
"""

import os
import re
import time
import argparse
import subprocess
from pathlib import Path
import sys
from datetime import datetime

# ANSI colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header():
    """Print header for the progress monitor"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}AI-BOM Autopilot - Scan Progress Monitor{Colors.END}\n")
    print(f"{Colors.UNDERLINE}Monitoring scan progress in real-time...{Colors.END}\n")

def find_log_file():
    """Find the most recent log file in the logs directory"""
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(exist_ok=True)
        print(f"Created logs directory: {log_dir}")
        return None
        
    log_files = sorted(log_dir.glob("*.log"), key=os.path.getmtime, reverse=True)
    if not log_files:
        return None
    return log_files[0]

def monitor_scan_progress(follow=True):
    """Monitor and display scan progress"""
    print_header()
    
    log_file = find_log_file()
    if not log_file:
        print(f"{Colors.RED}No log files found. Starting a new scan will create logs.{Colors.END}")
        return
    
    print(f"Monitoring log file: {log_file}\n")
    
    # Track which steps have been completed
    steps = {
        "plan": {"completed": False, "message": "Planning scan..."},
        "git_scan": {"completed": False, "message": "Scanning Git repository..."},
        "hf_scan": {"completed": False, "message": "Fetching HuggingFace cards..."},
        "runtime": {"completed": False, "message": "Collecting runtime artifacts..."},
        "normalize": {"completed": False, "message": "Normalizing artifacts..."},
        "embed": {"completed": False, "message": "Creating embeddings..."},
        "bom": {"completed": False, "message": "Generating BOM..."},
        "diff": {"completed": False, "message": "Generating diff..."},
        "policies": {"completed": False, "message": "Checking policies..."},
        "notify": {"completed": False, "message": "Sending notifications..."}
    }
    
    # State tracking
    last_position = 0
    models_found = 0
    datasets_found = 0
    prompts_found = 0
    tools_found = 0
    files_scanned = 0
    
    # Monitor the log file for progress updates
    try:
        while True:
            with open(log_file, 'r') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()
                
            if new_lines:
                for line in new_lines:
                    # Check for step completion
                    for step, info in steps.items():
                        if not info["completed"] and f"Node _{step}_node completed" in line:
                            steps[step]["completed"] = True
                            print(f"{Colors.GREEN}✓ {info['message']}{Colors.END}")
                    
                    # Check for specific information
                    if "Normalized" in line and "models" in line:
                        match = re.search(r"Normalized (\d+) models, (\d+) datasets, (\d+) prompts, (\d+) tools", line)
                        if match:
                            models_found = int(match.group(1))
                            datasets_found = int(match.group(2))
                            prompts_found = int(match.group(3))
                            tools_found = int(match.group(4))
                            print(f"{Colors.BLUE}ℹ Found: {models_found} models, {datasets_found} datasets, "
                                  f"{prompts_found} prompts, {tools_found} tools{Colors.END}")
                    
                    # Look for specific ML frameworks detection
                    if "framework detected:" in line.lower():
                        framework_match = re.search(r"Framework detected: (\w+)", line, re.IGNORECASE)
                        if framework_match:
                            framework = framework_match.group(1)
                            print(f"{Colors.GREEN}✓ ML Framework detected: {framework}{Colors.END}")
                    
                    # Look for specific model architectures detection
                    if "model type detected:" in line.lower():
                        model_match = re.search(r"Model type detected: (\w+)", line, re.IGNORECASE)
                        if model_match:
                            model_type = model_match.group(1)
                            print(f"{Colors.GREEN}✓ Model architecture detected: {model_type}{Colors.END}")
                    
                    if "Found" in line and "candidate artifacts" in line:
                        match = re.search(r"Found (\d+) candidate artifacts", line)
                        if match:
                            files_scanned = int(match.group(1))
                            print(f"{Colors.BLUE}ℹ Scanned {files_scanned} files{Colors.END}")
                    
                    # Check for errors
                    if "ERROR" in line:
                        print(f"{Colors.RED}! Error: {line.strip()}{Colors.END}")
                    
                    # Check for workflow completion
                    if "ML-BOM scan completed" in line:
                        print(f"\n{Colors.GREEN}✓ Scan completed successfully!{Colors.END}")
                        print(f"\n{Colors.BOLD}Scan Summary:{Colors.END}")
                        print(f"  - Files scanned: {files_scanned}")
                        print(f"  - Models detected: {models_found}")
                        print(f"  - Datasets detected: {datasets_found}")
                        print(f"  - Prompts detected: {prompts_found}")
                        print(f"  - Tools detected: {tools_found}")
                        if not follow:
                            return
            
            if not follow:
                return
                
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.END}")

def main():
    parser = argparse.ArgumentParser(description='Monitor AI-BOM Autopilot scan progress')
    parser.add_argument('--once', action='store_true', help='Check log once without continuous monitoring')
    args = parser.parse_args()
    
    monitor_scan_progress(follow=not args.once)

if __name__ == "__main__":
    main()
