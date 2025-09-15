# Embedding Service Documentation

## Overview

The EmbeddingService is a core component of the ML-BOM Autopilot system that handles text chunking, embedding generation, and hybrid search functionality. It supports multiple embedding providers and implements Reciprocal Rank Fusion (RRF) for combining vector and keyword search results.

## Features

### Multi-Provider Support
- **OpenAI**: Uses text-embedding-3-small (1536 dimensions) by default
- **Gemini**: Uses models/embedding-001 (768 dimensions) by default
- Configurable via environment variables

### Text Processing
- **Intelligent Chunking**: Splits long documents into overlapping chunks
- **Token-Aware**: Uses tiktoken for accurate token counting
- **Configurable Limits**: Default 800 tokens per chunk with 100 token overlap

### Hybrid Search
- **Vector Search**: ANN search using TiDB VEC_COSINE_DISTANCE
- **Keyword Search**: FULLTEXT search with BM25 fallback
- **RRF Fusion**: Combines results using Reciprocal Rank Fusion algorithm

### Reference Type Detection
- **README**: README.md files
- **CONFIG**: .yaml, .yml, .json files  
- **FILE**: All other files

## Configuration

### Environment Variables

```bash
# Embedding Provider Configuration
EMBED_PROVIDER=openai          # or 'gemini'
EMBEDDING_DIM=1536            # Must match provider output

# OpenAI Configuration
OPENAI_API_KEY=sk-your-key
EMBEDDING_MODEL=text-embedding-3-small

# Gemini Configuration  
GEMINI_API_KEY=your-gemini-key
EMBEDDING_MODEL=models/embedding-001
```

### Provider Switching

To switch from OpenAI to Gemini:

1. Update environment variables:
   ```bash
   EMBED_PROVIDER=gemini
   EMBEDDING_DIM=768
   GEMINI_API_KEY=your-key
   ```

2. Run database migration to resize vector column:
   ```sql
   ALTER TABLE evidence_chunks MODIFY COLUMN emb VECTOR(768);
   ```

## Usage

### Basic Initialization

```python
from core.embeddings.embedder import EmbeddingService

# Initialize service (reads config from environment)
service = EmbeddingService()
```

### Processing Evidence

```python
from core.schemas.models import ScanState, Project

# Create scan state
project = Project(id=1, name="test", repo_url="https://github.com/test/repo")
state = ScanState(
    project=project,
    commit_sha="abc123",
    files=["main.py", "README.md", "config.yaml"]
)

# Process evidence (chunks, embeds, and stores)
result_state = service.process_evidence(state)
print(f"Created {len(result_state.evidence_chunks)} evidence chunks")
```

### Hybrid Search

```python
# Search for similar content
results = service.search_similar(
    project_id=1,
    query="machine learning model training",
    limit=10
)

for result in results:
    print(f"File: {result['ref_path']}")
    print(f"Text: {result['text'][:100]}...")
    print(f"RRF Score: {result.get('rrf_score', 'N/A')}")
    print()
```

### Manual Text Chunking

```python
# Chunk a long document
long_text = "Your very long document content here..."
chunks = service._split_text(long_text)

print(f"Split into {len(chunks)} chunks")
for i, chunk in enumerate(chunks):
    token_count = len(service.encoding.encode(chunk))
    print(f"Chunk {i}: {token_count} tokens")
```

## Database Schema

The service works with the `evidence_chunks` table:

```sql
CREATE TABLE evidence_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    ref_type ENUM('file', 'card', 'config', 'readme') NOT NULL,
    ref_path VARCHAR(512) NOT NULL,
    commit_sha VARCHAR(40),
    chunk_ix INT NOT NULL,
    text TEXT NOT NULL,
    token_count INT NOT NULL,
    emb VECTOR(1536),  -- Dimension depends on provider
    meta JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_project_ref (project_id, ref_path),
    INDEX idx_commit (commit_sha),
    FULLTEXT KEY ft_text (text)  -- If supported by TiDB region
);
```

## Search Algorithms

### Vector Search (ANN)

Uses TiDB's vector functions for semantic similarity:

```sql
SELECT id, ref_path, text, 
       VEC_COSINE_DISTANCE(emb, :query_vector) AS distance
FROM evidence_chunks
WHERE project_id = :project_id
ORDER BY distance ASC
LIMIT :limit;
```

### Keyword Search

**FULLTEXT (when available):**
```sql
SELECT id, ref_path, text,
       MATCH(text) AGAINST (:query IN NATURAL LANGUAGE MODE) AS score
FROM evidence_chunks  
WHERE project_id = :project_id
AND MATCH(text) AGAINST (:query IN NATURAL LANGUAGE MODE)
ORDER BY score DESC;
```

**BM25 Fallback:**
Uses the `rank-bm25` library for in-application keyword scoring when FULLTEXT is unavailable.

### Reciprocal Rank Fusion (RRF)

Combines vector and keyword results using the formula:

```
RRF_score = 1/(k + vector_rank) + 1/(k + keyword_rank)
```

Where `k=60` (standard RRF parameter) and ranks start from 1.

## Error Handling

### Graceful Degradation

1. **No Vector Support**: Skips embedding generation, uses keyword-only search
2. **No FULLTEXT**: Falls back to BM25 in-application search  
3. **No Embedding Client**: Logs warning, continues without embeddings
4. **API Failures**: Logs errors, continues processing other chunks

### Logging

The service provides comprehensive logging:

```
INFO: Active embedding provider: openai, dimensions: 1536
INFO: Embedded batch 1/3 using openai
WARNING: Vector functions not available: <error>
INFO: FTS disabled -> BM25(app)
ERROR: Failed to embed batch 2: <error>
```

## Performance Considerations

### Chunking
- **Token Limits**: 800 tokens per chunk (configurable)
- **Overlap**: 100 tokens between chunks (configurable)
- **Memory**: Processes chunks in batches to manage memory usage

### Embedding
- **Batch Size**: 100 texts per API call (configurable)
- **Rate Limits**: Respects provider rate limits with error handling
- **Caching**: Deduplicates chunks by content hash

### Search
- **Vector Index**: Relies on TiDB's vector indexing for performance
- **Result Limits**: Fetches 2x limit for RRF fusion, returns top results
- **Fallback Chain**: Vector → FULLTEXT → BM25 → LIKE search

## Testing

Run the test suite:

```bash
# Unit tests
python test_embeddings.py

# Integration tests  
python test_embeddings_integration.py

# Usage examples
python example_embeddings_usage.py
```

## Requirements Compliance

This implementation satisfies **Requirement 6.1** from the ML-BOM Autopilot specification:

✅ **Text Chunking**: Intelligent chunking with token-aware splitting  
✅ **Embedding Generation**: Multi-provider support (OpenAI, Gemini)  
✅ **Vector Storage**: Proper VECTOR column format for TiDB  
✅ **Hybrid Search**: ANN + FULLTEXT/BM25 with RRF fusion  
✅ **Graceful Fallback**: Automatic degradation when features unavailable  

## Troubleshooting

### Common Issues

**"No embedding client available"**
- Check API keys in environment variables
- Verify provider is set correctly (openai/gemini)

**"Vector functions not available"**  
- TiDB cluster may not support vector functions
- Service will continue with keyword-only search

**"FTS disabled -> BM25(app)"**
- TiDB region doesn't support FULLTEXT search
- Automatic fallback to BM25 library

**Dimension mismatch errors**
- Ensure EMBEDDING_DIM matches provider output
- Run migration to resize vector column if needed