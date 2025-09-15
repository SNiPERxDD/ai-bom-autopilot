# AI-BOM Autopilot UI

A simple Streamlit-based single-page application for managing AI/ML Bill of Materials (BOM) scans and policy compliance.

## Features

### Main Interface
- **Project Selector**: Choose from available projects
- **Run Scan Button**: Execute ML-BOM scans with optional dry-run mode
- **Health Status**: Real-time indicators for system health (🟢/🟡/🔴)

### Results Tabs
1. **📋 BOM Tab**: View generated Bill of Materials with component breakdown
2. **🔄 Diff Tab**: Compare BOM versions and see changes
3. **⚠️ Policy Tab**: Review policy violations with action buttons
4. **📤 Actions Tab**: View notification history and external integrations

### Key Capabilities
- **Dry Run Mode**: Test scans without making changes or sending notifications
- **Action Triggers**: Send Slack notifications or create Jira tickets directly from policy events
- **Real-time Health Monitoring**: Database, vector search, full-text search, and API key status
- **Interactive Results**: Expandable sections, metrics, and visual charts

## Usage

### Starting the UI
```bash
# From the ai-bom-autopilot directory
streamlit run apps/ui/streamlit_app.py
```

The UI will be available at http://localhost:8501

### Prerequisites
- Backend API running on http://localhost:8000
- At least one project created in the system
- Proper environment configuration (.env file)

### Workflow
1. **Select Project**: Choose from the dropdown
2. **Configure Scan**: Toggle dry-run mode if needed
3. **Run Scan**: Click the "🚀 Run Scan" button
4. **Review Results**: Use the tabs to examine BOM, diffs, policy events, and actions
5. **Take Action**: Use action buttons to send notifications for policy violations

### Health Status Indicators
- **🟢 DB**: Database connection healthy
- **🟢 Vector**: Vector search available
- **🟢 FTS** / **🟡 BM25**: Full-text search status (FTS preferred, BM25 fallback)
- **🟢 API Keys**: External service credentials configured
- **🟢 System**: Overall system health

### Action Buttons
- **📢 Send to Slack**: Send policy violation alerts to configured Slack channels
- **🎫 Create Jira Ticket**: Create tickets for policy violations in configured Jira projects

## Requirements

See `requirements.txt` for full dependencies. Key UI dependencies:
- `streamlit>=1.28.1`
- `requests>=2.31.0`
- `pandas>=2.1.3`
- `plotly>=5.17.0`

## API Integration

The UI communicates with the FastAPI backend through these endpoints:
- `GET /health` - System health check
- `GET /projects` - List projects
- `POST /scan` - Execute scans
- `GET /projects/{id}/boms` - Get BOMs
- `GET /projects/{id}/diffs` - Get diffs
- `GET /projects/{id}/policy-events` - Get policy events
- `GET /projects/{id}/actions` - Get actions
- `POST /projects/{id}/policy-events/{event_id}/notify/slack` - Send Slack notification
- `POST /projects/{id}/policy-events/{event_id}/notify/jira` - Create Jira ticket