#!/bin/bash

# AI-BOM Autopilot - Quick Start Script

set -e

# Function to handle cleanup on script exit
cleanup() {
  echo "� Stopping services..."
  if [ -n "$API_PID" ]; then kill $API_PID 2>/dev/null || true; fi
  if [ -n "$UI_PID" ]; then kill $UI_PID 2>/dev/null || true; fi
  exit 0
}

# Set up trap for Ctrl+C and script exit
trap cleanup INT TERM EXIT

echo "�🚀 Starting AI-BOM Autopilot..."

# Get absolute path to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copying from .env.example..."
    cp .env.example .env
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source ".venv/bin/activate"

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Set Python path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Run migrations
echo "🗄️ Running database migrations..."
python -m core.db.migrations up

# Start API server in background
echo "🌐 Starting API server..."
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API to start..."
sleep 15

# Start Streamlit UI
echo "🎨 Starting Streamlit UI..."
export API_URL="http://127.0.0.1:8000"
streamlit run "$SCRIPT_DIR/apps/ui/streamlit_app.py" --server.port 8501 --server.address 127.0.0.1 --browser.serverAddress 127.0.0.1 --server.headless=false &
UI_PID=$!

echo "✅ AI-BOM Autopilot is running!"
echo ""
echo "🌐 API: http://127.0.0.1:8000"
echo "🎨 UI:  http://127.0.0.1:8501"
echo ""
echo "📱 Open your browser to http://127.0.0.1:8501 to access the UI"
echo ""
echo "Press Ctrl+C to stop all services"
echo "Or run ./cleanup.sh to stop all processes"

# Keep the script running until Ctrl+C is pressed
wait