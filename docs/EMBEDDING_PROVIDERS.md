# Multi-Provider Embedding Support

This document describes the multi-provider embedding support implemented in ML-BOM Autopilot, which allows switching between OpenAI and Gemini embedding providers.

## Overview

The embedding service supports multiple providers to give flexibility in cost optimization, performance tuning, and vendor independence. The system automatically handles dimension differences and provides proper validation.

## Supported Providers

### OpenAI
- **Provider ID**: `openai`
- **Default Model**: `text-embedding-3-small`
- **Default Dimensions**: 1536
- **Supported Dimensions**: 1536 (small), 3072 (large)
- **API Key**: `OPENAI_API_KEY`

### Gemini
- **Provider ID**: `gemini`
- **Default Model**: `models/embedding-001`
- **Default Dimensions**: 768
- **API Key**: `GEMINI_API_KEY`

## Configuration

### Environment Variables

```bash
# Choose your provider
EMBED_PROVIDER=openai  # or 'gemini'

# Set dimensions (REQUIRED)
EMBEDDING_DIM=1536     # Must match provider output

# Provider-specific API keys
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-api-key

# Optional: Override default models
EMBEDDING_MODEL=text-embedding-3-small  # For OpenAI
# EMBEDDING_MODEL=models/embedding-001   # For Gemini
```

### OpenAI Configuration Example

```bash
EMBED_PROVIDER=openai
EMBEDDING_DIM=1536
OPENAI_API_KEY=sk-proj-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
```

### Gemini Configuration Example

```bash
EMBED_PROVIDER=gemini
EMBEDDING_DIM=768
GEMINI_API_KEY=AIzaSyB-your-key-here
EMBEDDING_MODEL=models/embedding-001
```

## Switching Providers

### Step 1: Update Environment Variables
Change your `.env` file to use the desired provider:

```bash
# From OpenAI to Gemini
EMBED_PROVIDER=gemini
EMBEDDING_DIM=768
GEMINI_API_KEY=your-gemini-key
```

### Step 2: Database Migration (if needed)
If switching between providers with different dimensions, you may need to run a database migration:

```sql
-- Example: Switching from OpenAI (1536D) to Gemini (768D)
ALTER TABLE evidence_chunks MODIFY COLUMN emb VECTOR(768);
```

### Step 3: Restart Application
The embedding service will automatically detect the new configuration on startup.

## Startup Logging

The service provides detailed startup logging to help verify configuration:

```
🚀 Embedding Service Initialized
   Provider: openai
   Model: text-embedding-3-small
   Dimensions: 1536
   Client Available: True
```

## Validation and Testing

### Configuration Validation
```python
from core.embeddings.embedder import EmbeddingService

service = EmbeddingService()
validation = service.validate_provider_config()

print(f"Valid: {validation['config_valid']}")
print(f"Warnings: {validation['warnings']}")
print(f"Errors: {validation['errors']}")
```

### Test Scripts
- `test_embedding_providers.py` - Basic provider functionality
- `test_embedding_integration.py` - Integration with existing components

## Troubleshooting

### Common Issues

1. **Dimension Mismatch**
   ```
   Error: Expected 1536 dimensions, got 768
   ```
   **Solution**: Update `EMBEDDING_DIM` to match your provider's output.

2. **API Key Not Configured**
   ```
   Warning: OpenAI API key not configured or using test key
   ```
   **Solution**: Set the appropriate API key environment variable.

3. **Package Missing**
   ```
   Error: google-generativeai package not installed
   ```
   **Solution**: Install the required package: `pip install google-generativeai`

### Validation Warnings

The system will warn about unusual dimension configurations:

- OpenAI with non-standard dimensions (not 1536 or 3072)
- Gemini with non-standard dimensions (not 768)

These warnings don't prevent operation but suggest reviewing your configuration.

## Performance Considerations

### Provider Comparison

| Provider | Dimensions | Cost | Speed | Quality |
|----------|------------|------|-------|---------|
| OpenAI   | 1536       | $$   | Fast  | High    |
| OpenAI   | 3072       | $$$  | Medium| Higher  |
| Gemini   | 768        | $    | Fast  | Good    |

### Recommendations

- **Development/Testing**: Use Gemini for lower costs
- **Production**: Use OpenAI for higher quality embeddings
- **Large Scale**: Consider OpenAI's batch API for cost optimization

## Database Schema Impact

The `evidence_chunks` table stores embeddings in a `VECTOR` column:

```sql
CREATE TABLE evidence_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- ... other columns ...
    emb VECTOR(1536),  -- Dimension must match provider
    -- ... other columns ...
);
```

When switching providers with different dimensions, the vector column must be resized.

## Integration Points

The multi-provider system integrates with:

1. **Hybrid Search Engine** - Uses embeddings for ANN search
2. **Evidence Processing** - Embeds text chunks during scanning
3. **Database Storage** - Stores embeddings with proper dimensions
4. **Workflow Orchestration** - Provides embedding capabilities to LangGraph

## Requirements Compliance

This implementation satisfies the following requirements:

- **7.1**: OpenAI provider with 1536-dimension support
- **7.2**: Gemini provider with 768-dimension support  
- **7.4**: Startup logging for active provider and dimensions
- **7.5**: Explicit EMBEDDING_DIM requirement for data consistency

## Future Enhancements

Potential future improvements:

1. **Additional Providers**: Azure OpenAI, Cohere, etc.
2. **Automatic Migration**: Scripts to handle dimension changes
3. **Provider Fallback**: Automatic failover between providers
4. **Batch Processing**: Optimized batch embedding for large datasets