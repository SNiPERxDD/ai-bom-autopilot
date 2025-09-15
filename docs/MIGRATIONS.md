# ML-BOM Autopilot Database Migrations

This document describes the database migration system for ML-BOM Autopilot.

## Overview

The migration system provides:
- **Automated schema creation** for all required tables
- **FULLTEXT search detection** with automatic BM25 fallback
- **Vector function testing** for TiDB compatibility
- **Comprehensive self-test** for system health
- **CLI interface** for easy operation

## Database Schema

The system creates the following tables:

### Core Tables
- `projects` - Top-level project organization
- `models` - AI/ML models with metadata and licensing
- `datasets` - Training/validation datasets with provenance  
- `prompts` - System and user prompts with versioning
- `prompt_blobs` - De-duplicated prompt content storage
- `tools` - AI tools and frameworks

### BOM Management
- `boms` - Versioned CycloneDX BOM JSON storage
- `bom_diffs` - Structural differences between BOM versions
- `evidence_chunks` - Text chunks for hybrid search with embeddings

### Policy & Governance
- `policies` - Configurable rules for compliance checking
- `policy_overrides` - Approved exceptions with expiration
- `policy_events` - Detected violations and their severity
- `suppressions` - Temporary suppression of specific events
- `actions` - Audit log of external notifications and API calls

## Usage

### Running Migrations

```bash
# Run all migrations and seed default policies
python -m core.db.migrations up
```

### System Health Check

```bash
# Run comprehensive diagnostics
python -m core.db.migrations selftest
```

### Vector Column Resize

```bash
# Auto-resize based on current EMBED_PROVIDER configuration
python -m core.db.migrations resize-vector

# Manual resize to specific dimension
python -m core.db.migrations resize-vector --dimension 768
python -m core.db.migrations resize-vector --dimension 1536

# Check current vector column status
python -m core.db.resize_vector_migration status
```

### Programmatic Usage

```python
from core.db.migrations import run_migrations, selftest, FTS_ENABLED

# Run migrations
run_migrations()

# Check if FULLTEXT search is available
if FTS_ENABLED:
    print("Using TiDB FULLTEXT search")
else:
    print("Using BM25 fallback")

# Run diagnostics
selftest()
```

## Features

### Vector Column Resize Migration

The system provides safe migration capabilities for resizing the embedding vector column when switching between different embedding providers:

- **Automatic Detection**: Detects current vector dimension and provider configuration
- **Data Preservation**: Creates backups before migration and preserves existing data structure
- **Rollback Safety**: Uses transactions to ensure safe rollback on failure
- **Provider Validation**: Warns about unusual dimension configurations for known providers
- **Index Management**: Automatically recreates vector indexes after column resize

**Supported Dimensions:**
- OpenAI: 1536 dimensions (text-embedding-3-small) or 3072 (text-embedding-3-large)
- Gemini: 768 dimensions (models/embedding-001)

**Migration Process:**
1. Validates table existence and vector support
2. Creates backup of existing vector data
3. Clears vector column (TiDB requirement for column resize)
4. Resizes column to new dimension
5. Recreates vector index
6. Validates successful migration

### FULLTEXT Search Detection

The system automatically detects if TiDB FULLTEXT indexes are supported:

- **Supported**: Uses `MATCH(...) AGAINST(...)` for keyword search
- **Not Supported**: Falls back to in-app BM25 using `rank-bm25` library
- Sets global `FTS_ENABLED` flag for runtime decisions

### Vector Function Testing

Tests TiDB vector capabilities:
- Validates `VEC_COSINE_DISTANCE()` function availability
- Configures appropriate vector column dimensions
- Logs vector search capabilities

### Self-Test Function

The `selftest()` function provides comprehensive diagnostics:

1. **Database Connection** - Tests TiDB connectivity and version
2. **Vector Functions** - Validates vector search capabilities  
3. **Search Mode** - Reports FULLTEXT vs BM25 mode
4. **API Keys** - Checks configuration for:
   - OpenAI/Gemini embedding providers
   - Slack webhook URLs
   - Jira API credentials
   - HuggingFace tokens

### Default Policies

Seeds 5 starter policies:
- `missing_license` - Artifacts without SPDX licenses
- `unapproved_license` - Licenses not in allowlist
- `unknown_provider` - Models/datasets from unknown sources
- `model_bump_major` - Major version changes
- `prompt_changed_protected_path` - Changes to protected prompts

## Configuration

Required environment variables:

```bash
# TiDB Connection
TIDB_URL=gateway01.ap-southeast-1.prod.aws.tidbcloud.com
DB_USER=your-user.root
DB_PASS=your-password
DB_NAME=your-database

# Embedding Provider
EMBED_PROVIDER=openai  # or 'gemini'
OPENAI_API_KEY=sk-your-key
EMBEDDING_DIM=1536

# Optional: Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
JIRA_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-token
HF_TOKEN=your-hf-token
```

## Error Handling

The migration system includes robust error handling:

- **Connection failures** - Clear error messages with troubleshooting hints
- **Missing capabilities** - Graceful degradation (FTS → BM25)
- **Migration failures** - Transaction rollback and detailed logging
- **API key validation** - Startup checks with clear status indicators

## Testing

Run the test suite to verify migration functionality:

```bash
# Test migration structure (no DB required)
python test_migration_structure.py

# Test selftest function with mocks
python test_selftest_mock.py

# Full integration test (requires TiDB)
python test_migrations.py
```

## Troubleshooting

### Common Issues

1. **"Missing user name prefix"** - Check TiDB connection format
2. **"FULLTEXT not supported"** - Normal in some regions, BM25 fallback works
3. **"Vector functions unavailable"** - Check TiDB version and region
4. **API key errors** - Verify environment variable configuration

### Debug Mode

Enable detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m core.db.migrations selftest
```

## Architecture Notes

- Uses SQLAlchemy for database abstraction
- Supports both TiDB Cloud and self-hosted TiDB
- Vector columns adapt to embedding provider dimensions
- Global flags enable runtime capability detection
- CLI interface supports automation and CI/CD integration