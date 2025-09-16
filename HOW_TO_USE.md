# How to Use AI-BOM Autopilot

## Overview

AI-BOM Autopilot is a minimalist web interface for generating Machine Learning Bill of Materials (ML-BOM), tracking changes, and enforcing compliance policies. This guide will walk you through using all features of the system.

## Getting Started

### 1. Accessing the Interface

Open your web browser and navigate to:
```
http://127.0.0.1:8501
```

You'll see the main interface with:
- 🔍 **AI-BOM Autopilot** title
- **System Status** indicators
- **Project** dropdown selector
- **Welcome screen** with feature overview

### 2. Understanding System Status

The system status shows three key indicators:

- 🟢 **Database**: Connection to TiDB Serverless is healthy
- 🟢 **Vector Search**: Vector search capability is available  
- 🟡 **Full-text Search**: Either available (🟢) or using BM25 fallback (🟡)

## Working with Projects

### Creating a New Project

1. Click on the **Project** dropdown
2. Select "➕ Add New Project" from the bottom of the list
3. Fill out the project creation form:
   - **Project Name**: Choose a descriptive name (e.g., "my-ml-project")
   - **Repository URL**: Full GitHub URL (e.g., "https://github.com/user/repo")
   - **Default Branch**: Usually "main" or "master" (pre-filled as "main")
4. Click **Create Project**
5. The project will be added and appear in the dropdown

### Selecting a Project

1. Click on the **Project** dropdown
2. Choose from existing projects in the list
3. The interface will update to show project-specific information

## Running Scans

Once you have selected a project, you can run scans to generate ML-BOMs:

### Dry Run (Recommended for Testing)

1. Click the **🧪 Dry Run** button
2. This will:
   - Clone the repository (if not already cached)
   - Scan for ML artifacts (models, datasets, prompts, tools)
   - Generate a BOM without saving to database
   - Show progress: "Running dry run..."
   - Display results when complete

### Full Scan

1. Click the **🚀 Scan** button  
2. This will:
   - Perform all dry run steps
   - Save the BOM to the database
   - Create policy events if violations found
   - Generate diff if previous BOMs exist

## Viewing Results

The interface provides four tabs to view scan results:

### 📋 BOMs Tab

- Shows the latest generated Bill of Materials
- Displays component count and creation date
- Lists all discovered components with:
  - **Name**: Component identifier
  - **Type**: model, dataset, prompt, or tool
  - **Version**: Component version if available
  - **License**: SPDX license identifier or "N/A"

### 🔄 Changes Tab

- Shows differences between BOM versions
- Displays metrics for:
  - **Added**: New components found
  - **Modified**: Changed components
  - **Removed**: Components no longer found
- Only appears after running multiple scans

### ⚠️ Policies Tab

- Shows policy violations by severity:
  - 🔴 **High**: Critical issues requiring immediate attention
  - 🟡 **Medium**: Important issues to address
  - 🟢 **Low**: Minor issues for awareness
- Each violation shows:
  - Rule name and affected artifact
  - Detailed message explaining the issue
  - Action buttons for notifications

### 📤 Actions Tab

- Shows history of external notifications sent
- Displays timestamp and delivery status
- Shows payload and response details

## Taking Action on Policy Violations

When policy violations are found, you can take immediate action:

### Send Slack Notification

1. Navigate to the **⚠️ Policies** tab
2. Find the violation you want to report
3. Click **📢 Send to Slack**
4. A formatted message will be sent to the configured Slack channel

### Create Jira Ticket

1. Navigate to the **⚠️ Policies** tab  
2. Find the violation you want to track
3. Click **🎫 Create Jira Ticket**
4. A ticket will be created in the configured Jira project

## Understanding the Interface

### Clean, Minimalist Design

The interface follows these principles:
- **Essential features only**: No clutter or unnecessary elements
- **Clear visual hierarchy**: Important actions are prominent
- **Immediate feedback**: Status messages and progress indicators
- **Responsive layout**: Works on different screen sizes

### Error Handling

The system gracefully handles common issues:
- **API Connection Lost**: Shows error message and retry guidance
- **Invalid Repository URLs**: Clear error messages during project creation
- **Scan Failures**: Detailed error messages with troubleshooting hints

### Workflow Overview

1. **Create or select a project** → Specify which repository to scan
2. **Run a scan** → Discover ML artifacts and generate BOM
3. **Review results** → Examine components, changes, and policy violations
4. **Take action** → Send notifications for compliance issues
5. **Track progress** → Monitor actions and maintain audit trail

## Best Practices

### For First-Time Users

1. Start with a **dry run** to understand what will be scanned
2. Review the BOM output before running a full scan
3. Understand your organization's policy rules before taking action

### For Regular Use

1. Run scans after significant repository changes
2. Monitor the **Changes** tab to track drift over time
3. Address high-severity policy violations promptly
4. Use action notifications to maintain team awareness

### For Compliance

1. Maintain regular scanning schedule for critical projects
2. Document policy violations and remediation actions
3. Use Jira tickets for tracking compliance work
4. Review the audit trail in the Actions tab

## Troubleshooting

### Common Issues

**"Failed to load projects"**
- Check if the API server is running on port 8000
- Verify database connection in system status

**"Scan failed"**
- Ensure repository URL is accessible
- Check if repository requires authentication
- Verify network connectivity

**"No components found"**
- Repository may not contain ML artifacts
- Check if scanning patterns match your project structure

### Getting Help

The interface provides contextual error messages and status indicators to help diagnose issues. System status indicators show the health of core components.

---

*This guide covers the core functionality of AI-BOM Autopilot. The interface is designed to be intuitive and self-explanatory, with clear feedback for all user actions.*