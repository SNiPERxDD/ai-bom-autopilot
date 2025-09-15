#!/bin/bash

# Cleanup script for AI-BOM Autopilot
# This script finds and kills all running uvicorn and streamlit processes

echo "🧹 Cleaning up AI-BOM Autopilot processes..."

# Kill uvicorn processes (API servers)
echo "🔍 Looking for uvicorn processes..."
uvicorn_pids=$(pgrep -f "uvicorn.*apps.api.main")
if [ -n "$uvicorn_pids" ]; then
    echo "🛑 Killing uvicorn processes: $uvicorn_pids"
    kill $uvicorn_pids 2>/dev/null || true
else
    echo "✅ No uvicorn processes found"
fi

# Kill streamlit processes
echo "🔍 Looking for streamlit processes..."
streamlit_pids=$(pgrep -f "streamlit.*streamlit_app.py")
if [ -n "$streamlit_pids" ]; then
    echo "🛑 Killing streamlit processes: $streamlit_pids"
    kill $streamlit_pids 2>/dev/null || true
else
    echo "✅ No streamlit processes found"
fi

# Check for any remaining processes on common ports
echo "🔍 Checking for processes on common ports..."

# Check port 8000
port_8000_pid=$(lsof -ti :8000)
if [ -n "$port_8000_pid" ]; then
    echo "🛑 Killing process on port 8000: $port_8000_pid"
    kill $port_8000_pid 2>/dev/null || true
fi

# Check port 8001
port_8001_pid=$(lsof -ti :8001)
if [ -n "$port_8001_pid" ]; then
    echo "🛑 Killing process on port 8001: $port_8001_pid"
    kill $port_8001_pid 2>/dev/null || true
fi

# Check port 8002
port_8002_pid=$(lsof -ti :8002)
if [ -n "$port_8002_pid" ]; then
    echo "🛑 Killing process on port 8002: $port_8002_pid"
    kill $port_8002_pid 2>/dev/null || true
fi

# Check port 8501
port_8501_pid=$(lsof -ti :8501)
if [ -n "$port_8501_pid" ]; then
    echo "🛑 Killing process on port 8501: $port_8501_pid"
    kill $port_8501_pid 2>/dev/null || true
fi

# Check port 8502
port_8502_pid=$(lsof -ti :8502)
if [ -n "$port_8502_pid" ]; then
    echo "🛑 Killing process on port 8502: $port_8502_pid"
    kill $port_8502_pid 2>/dev/null || true
fi

echo "✅ Cleanup complete!"
echo "🚀 You can now run ./run.sh to start the application fresh"
