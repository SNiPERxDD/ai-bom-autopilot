# AI-BOM Autopilot Demo Guide

## Quick Demo (3 minutes)

### Prerequisites
1. TiDB Serverless account and connection string
2. OpenAI API key
3. Slack webhook URL (optional)
4. Jira credentials (optional)

### Setup (1 minute)

```bash
# Clone and setup
git clone <your-repo>
cd ai-bom-autopilot

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start the application
./run.sh
```

### Demo Script (2 minutes)

#### 1. Create Demo Project (30 seconds)
```bash
# In another terminal
cd ai-bom-autopilot
python seed/create_demo_project.py
```

This creates a sample ML project with:
- LLaMA 3.1 8B model references
- BERT model usage
- IMDB dataset
- Sample prompts
- Configuration files

#### 2. View Initial Scan Results (30 seconds)
- Open http://localhost:8501
- Navigate to "Scan Results" tab
- View the generated BOM with components:
  - 3 Models (LLaMA, BERT, GPT-4)
  - 2 Datasets (IMDB, Squad)
  - 2 Prompts
  - 2 Tools

#### 3. Trigger Policy Violations (30 seconds)
```bash
# Modify the sample project to trigger violations
cd /tmp/demo-repo  # Path shown by create_demo_project.py

# Change model to one with restrictive license
sed -i 's/meta-llama\/Llama-3.1-8B/meta-llama\/Llama-2-70b-chat-hf/g' train.py
sed -i 's/license: "custom"/license: "llama2"/g' config.yaml

# Commit changes
git add -A
git commit -m "Update to LLaMA 2 70B with restrictive license"
```

#### 4. Run Second Scan & Show Diff (30 seconds)
- In UI, click "Run Scan" button
- Navigate to "Diffs" tab to see:
  - Model version change (8B → 70B) = Major version bump
  - License change (custom → llama2) = Unapproved license
- Check "Policy Events" tab for violations:
  - 🔴 High: Unapproved license (llama2)
  - 🟡 Medium: Major model version bump

#### 5. View Notifications (30 seconds)
- Check "Actions" tab for:
  - ✅ Slack notification sent
  - ✅ Jira ticket created (if configured)
- Show actual Slack message and Jira ticket

### Key Demo Points

1. **Standards Compliance**: Generated CycloneDX ML-BOM validates against schema
2. **Hybrid Search**: Vector embeddings + full-text search for evidence
3. **Policy Engine**: Configurable rules with severity levels
4. **Audit Trail**: Every action logged with request/response
5. **Diff Engine**: Structural comparison with stable component IDs
6. **Integrations**: Slack/Jira notifications for compliance teams

### Demo Data Flow

```
Git Repo → Scan → Normalize → Embed → BOM → Diff → Policy → Notify
    ↓         ↓        ↓        ↓      ↓     ↓       ↓       ↓
  Files    HF Cards  SPDX    Vector  JSON  Changes Rules  Slack/Jira
```

### Troubleshooting

**Vector search not working?**
- Check TiDB capabilities in Health Check
- Falls back to BM25 automatically

**No HuggingFace cards found?**
- Check internet connection
- Models are cached for performance

**Slack/Jira not working?**
- Check credentials in .env
- View error details in Actions tab

### Extending the Demo

1. **Add more models**: Edit train.py with different HF model names
2. **Create custom policies**: Add rules in database
3. **Test different licenses**: Change config.yaml license field
4. **Add prompts**: Create files in prompts/ directory

## Production Deployment

For production use:
1. Use TiDB Dedicated for better performance
2. Set up proper CI/CD integration
3. Configure enterprise Slack/Jira instances
4. Add authentication and authorization
5. Set up monitoring and alerting