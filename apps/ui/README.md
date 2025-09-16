# AI-BOM Autopilot UI

A minimalist Streamlit-based single-page application for managing AI/ML Bill of Materials (BOM) scans and policy compliance.

## Features

### Clean, Minimalist Design
- **System Status Indicators**: Real-time health monitoring (🟢/🟡/🔴)
- **Project Management**: Dropdown selector with "Add New Project" option
- **Quick Actions**: Prominent Scan and Dry Run buttons
- **Tabbed Interface**: Organized results in BOMs, Changes, Policies, Actions tabs

### Core Capabilities
- **Project Creation**: Inline form for adding new projects directly from dropdown
- **Scan Operations**: Full scan and dry run modes with progress indication
- **Policy Compliance**: View violations by severity with action buttons
- **Notifications**: Send Slack alerts or create Jira tickets for policy violations
- **Change Tracking**: Compare BOM versions to identify drift

### Enhanced User Experience
- **Intuitive Navigation**: Single-page design with logical flow
- **Immediate Feedback**: Progress indicators and status messages
- **Error Handling**: Graceful degradation with helpful error messages
- **Responsive Layout**: Clean design that works on different screen sizes

## Usage

### Starting the UI
```bash
# From the ai-bom-autopilot directory
./run.sh
```

The minimalist UI will be available at http://localhost:8501

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