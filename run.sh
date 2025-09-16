#!/bin/bash

# AI-BOM Autopilot - Quick Start Script

set -e

# Function to handle cleanup on script exit
cleanup() {
  echo "🛑 Stopping services..."
  if [ -n "$API_PID" ]; then kill $API_PID 2>/dev/null || true; fi
  if [ -n "$UI_PID" ]; then kill $UI_PID 2>/dev/null || true; fi

 
  # Clean up temporary repositories (Task 3: Session cleanup)
  echo "🧹 Cleaning up temporary repositories..."
  if [ -d "/tmp/ai_bom_repos" ]; then
    rm -rf /tmp/ai_bom_repos
    echo "✅ Temporary repositories cleaned up"
  fi

  # Clean up any cloned repositories in the workspace
  find . -name ".git" -type d 2>/dev/null | grep -v "^./.git$" | while read gitdir; do
    repo_dir=$(dirname "$gitdir")
    if [ "$repo_dir" != "." ]; then
      echo "🗑️ Removing cloned repository: $repo_dir"
      rm -rf "$repo_dir"
    fi
  done
  # Unset all mapped env vars so they don’t persist
  unset DB_NAME DB_USER DB_PASS TIDB_URL
  unset OPENAI_API_KEY GEMINI_API_KEY SLACK_WEBHOOK_URL
  unset JIRA_URL JIRA_USERNAME JIRA_API_TOKEN JIRA_PROJECT_KEY
  unset HF_TOKEN DEBUG LOG_LEVEL DRY_RUN API_URL DATABASE_URL

  exit 0
}

# Set up trap for Ctrl+C and script exit
trap cleanup INT TERM EXIT

echo "🚀 Starting AI-BOM Autopilot..."

# === Copilot Agent Session Env Mapping ===
# If COPILOT_MCP_* vars exist, map them into the plain names the code expects.
export DB_NAME="${DB_NAME:-$COPILOT_MCP_DB_NAME}"
export DB_USER="${DB_USER:-$COPILOT_MCP_DB_USER}"
export DB_PASS="${DB_PASS:-$COPILOT_MCP_DB_PASS}"
export TIDB_URL="${TIDB_URL:-$COPILOT_MCP_TIDB_URL}"

export OPENAI_API_KEY="${OPENAI_API_KEY:-$COPILOT_MCP_OPENAI_API_KEY}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-$COPILOT_MCP_GEMINI_API_KEY}"
export SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-$COPILOT_MCP_SLACK_WEBHOOK_URL}"
export JIRA_URL="${JIRA_URL:-$COPILOT_MCP_JIRA_URL}"
export JIRA_USERNAME="${JIRA_USERNAME:-$COPILOT_MCP_JIRA_USERNAME}"
export JIRA_API_TOKEN="${JIRA_API_TOKEN:-$COPILOT_MCP_JIRA_API_TOKEN}"
export JIRA_PROJECT_KEY="${JIRA_PROJECT_KEY:-$COPILOT_MCP_JIRA_PROJECT_KEY}"
export HF_TOKEN="${HF_TOKEN:-$COPILOT_MCP_HF_TOKEN}"

export DEBUG="${DEBUG:-true}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export DRY_RUN="${DRY_RUN:-false}"

# Get absolute path to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copying from .env.example..."
    cp .env.example .env
fi

# Load .env ONLY if environment variables aren't already set (local dev only)
if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ] || [ -z "$TIDB_URL" ]; then
  echo "📄 Loading .env for local development..."
  set -a
  source .env
  set +a
else
  echo "🔧 Using injected environment variables (Copilot MCP mode)"
fi

# Ensure DB vars are set
if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ] || [ -z "$TIDB_URL" ]; then
  echo "❌ Missing DB credentials. Check .env or Copilot MCP secrets."
  cleanup
fi

# Build DATABASE_URL for TiDB Cloud (MySQL-compatible, SSL required)
export DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASS}@${TIDB_URL}/${DB_NAME}?ssl=true"

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
echo "🗄️ Running database migrations with $DATABASE_URL"
python -m core.db.migrations up || {
  echo "❌ Migration failed. Check DB creds or connectivity."
  cleanup
}

# Start API server in background
echo "🌐 Starting API server..."
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API to start..."
sleep 15

# Start Streamlit UI (using simplified version)
echo "🎨 Starting Minimalist Streamlit UI..."
export API_URL="http://127.0.0.1:8000"
streamlit run "$SCRIPT_DIR/apps/ui/streamlit_app_simple.py" \
  --server.port 8501 \
  --server.address 127.0.0.1 \
  --browser.serverAddress 127.0.0.1 \
  --server.headless=true \
  --client.toolbarMode=minimal &
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
