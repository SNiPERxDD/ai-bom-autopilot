# Vector Column Migration Guide

This guide explains how to safely migrate the embedding vector column when switching between different embedding providers in ML-BOM Autopilot.

## Overview

ML-BOM Autopilot supports multiple embedding providers with different vector dimensions:

- **OpenAI**: 1536 dimensions (text-embedding-3-small) or 3072 (text-embedding-3-large)
- **Gemini**: 768 dimensions (models/embedding-001)

When switching providers, you need to resize the database vector column to match the new provider's output dimensions.

## Quick Start

### 1. Check Current Status

```bash
python -m core.db.resize_vector_migration status
```

This shows:
- Current vector column dimension
- Number of rows with vector data
- Current provider configuration
- Any dimension mismatches

### 2. Auto-Migration (Recommended)

```bash
# Update your .env file first:
EMBED_PROVIDER=gemini
EMBEDDING_DIM=768
GEMINI_API_KEY=your-key

# Then run auto-migration:
python -m core.db.migrations resize-vector
```

### 3. Manual Migration

```bash
# Resize to specific dimension:
python -m core.db.migrations resize-vector --dimension 768
python -m core.db.migrations resize-vector --dimension 1536
```

## Migration Process

The migration follows these steps:

1. **Validation**: Checks table existence and vector support
2. **Backup**: Creates backup table with existing vector data
3. **Clear**: Removes vector data (TiDB requirement for column resize)
4. **Resize**: Alters column to new dimension: `VECTOR(new_dim)`
5. **Index**: Recreates vector index for optimal performance
6. **Validate**: Confirms successful migration

## Common Scenarios

### OpenAI to Gemini

```bash
# 1. Update environment
EMBED_PROVIDER=gemini
EMBEDDING_DIM=768
GEMINI_API_KEY=AIzaSyB...

# 2. Run migration
python -m core.db.migrations resize-vector

# 3. Re-embed existing data (if any)
# Your application will need to re-process existing chunks
```

### Gemini to OpenAI

```bash
# 1. Update environment
EMBED_PROVIDER=openai
EMBEDDING_DIM=1536
OPENAI_API_KEY=sk-proj...

# 2. Run migration
python -m core.db.migrations resize-vector
```

### OpenAI Model Upgrade

```bash
# Switching from text-embedding-3-small (1536D) to text-embedding-3-large (3072D)
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072

python -m core.db.migrations resize-vector --dimension 3072
```

## Data Preservation

### What's Preserved
- All table structure and indexes
- All non-vector data (text, metadata, etc.)
- Backup of original vector data

### What's Cleared
- Vector embeddings in the `emb` column
- This is required by TiDB for column dimension changes

### After Migration
- Re-embed existing chunks with the new provider
- The backup table contains original vectors if needed
- All other data remains intact

## Safety Features

### Transaction Safety
- Uses database transactions for rollback on failure
- Safe to retry if migration fails
- No data loss on rollback

### Backup Creation
- Automatic backup before migration
- Backup table: `evidence_chunks_backup_<timestamp>`
- Contains all original vector data

### Validation
- Pre-migration checks (table exists, vector support)
- Post-migration validation (correct dimension)
- Configuration mismatch warnings

## Troubleshooting

### Common Issues

**"Table does not exist"**
```bash
# Run initial migrations first
python -m core.db.migrations up
```

**"Vector functions not supported"**
- Check TiDB version and region
- Some TiDB regions don't support vector functions
- Contact TiDB support for availability

**"Dimension mismatch"**
```bash
# Check current status
python -m core.db.resize_vector_migration status

# Run migration to fix
python -m core.db.migrations resize-vector
```

**Migration fails mid-process**
- Transaction automatically rolls back
- Safe to retry the migration
- Check logs for specific error details

### Debug Mode

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m core.db.migrations resize-vector
```

## CLI Reference

### Status Command
```bash
python -m core.db.resize_vector_migration status
```
Shows current configuration and any issues.

### Auto Migration
```bash
python -m core.db.migrations resize-vector
```
Automatically resizes based on `EMBED_PROVIDER` and `EMBEDDING_DIM`.

### Manual Migration
```bash
python -m core.db.migrations resize-vector --dimension 768
python -m core.db.migrations resize-vector --dimension 1536
python -m core.db.migrations resize-vector --dimension 3072
```

### Fast Migration (No Backup)
```bash
python -m core.db.resize_vector_migration resize --dimension 768 --no-preserve
```
Skips backup creation for faster migration (use with caution).

## Best Practices

1. **Always check status first** to understand current state
2. **Update environment variables** before running migration
3. **Test with small datasets** before production migration
4. **Keep backups** of important vector data
5. **Re-embed incrementally** after migration to avoid API rate limits
6. **Monitor logs** during migration for any warnings

## Integration with Application

After migration, your application should:

1. **Detect dimension changes** and re-embed existing chunks
2. **Use new provider** for all new embeddings
3. **Update search queries** if needed (usually automatic)
4. **Monitor performance** with new provider

The embedding service automatically detects the new configuration and logs the active provider and dimensions on startup.