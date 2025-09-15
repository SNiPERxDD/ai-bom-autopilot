# Usage Examples

This directory contains practical examples and tutorials for using AI-BOM Autopilot components.

## Examples Overview

### 🧠 Embedding Service Examples
**`example_embeddings_usage.py`**
- Text chunking and token counting
- Multi-provider embedding generation (OpenAI/Gemini)
- Reference type detection for different file types
- Evidence chunk creation and management
- Reciprocal Rank Fusion (RRF) demonstration

### 🔍 Hybrid Search Examples
**`example_hybrid_search_usage.py`**
- Search capabilities reporting and configuration
- Vector similarity search with VEC_COSINE_DISTANCE
- FULLTEXT search with BM25 fallback
- Hybrid search combining vector and keyword results
- Search result formatting and serialization

### 🤗 HuggingFace Integration Examples
**`example_scan_hf_usage.py`**
- Single model/dataset card fetching
- Batch fetching with caching
- Version-specific card retrieval
- Cache management and statistics
- Slug validation and error handling

### 🔄 Vector Migration Examples
**`example_vector_migration.py`**
- Provider switching (OpenAI ↔ Gemini)
- Vector column dimension migration
- Migration status checking
- Configuration validation
- Database schema updates

## Quick Start Examples

### Basic Embedding Usage
```python
from core.embeddings.embedder import EmbeddingService

# Initialize service
service = EmbeddingService()

# Chunk and embed text
text = "Your ML documentation or code here..."
chunks = service._split_text(text)

# Generate embeddings
for chunk in chunks:
    embedding = service._embed_text(chunk)
    print(f"Chunk: {len(chunk)} chars, Embedding: {len(embedding)} dims")
```

### Hybrid Search Usage
```python
from core.search.engine import HybridSearchEngine

# Initialize search engine
search_engine = HybridSearchEngine()

# Perform hybrid search
results = search_engine.search(
    project_id=1,
    query_text="machine learning model training",
    top_k=10
)

for result in results:
    print(f"File: {result.ref_path}")
    print(f"Score: {result.score:.4f}")
    print(f"Type: {result.search_type}")
```

### HuggingFace Card Fetching
```python
from core.scan_hf.fetcher import HuggingFaceFetcher

# Initialize fetcher
fetcher = HuggingFaceFetcher(cache_ttl_hours=24)

# Fetch model card
card = fetcher.fetch_card("bert-base-uncased")
print(f"Model: {card.slug}")
print(f"License: {card.license}")
print(f"Pipeline: {card.pipeline_tag}")
```

### Vector Migration
```python
from core.db.resize_vector_migration import (
    get_current_vector_dimension,
    check_vector_support
)

# Check current status
if check_vector_support():
    current_dim = get_current_vector_dimension()
    print(f"Current dimension: {current_dim}")
    
    # Migration would be done via CLI:
    # python -m core.db.migrations resize-vector --dimension 768
```

## Running Examples

### Prerequisites
```bash
# Ensure environment is configured
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
pip install -r requirements.txt

# Initialize database (for examples that need it)
python -m core.db.migrations up
```

### Execute Examples
```bash
# Run individual examples
python examples/example_embeddings_usage.py
python examples/example_hybrid_search_usage.py
python examples/example_scan_hf_usage.py
python examples/example_vector_migration.py

# Run all examples
for example in examples/example_*.py; do
    echo "Running $example..."
    python "$example"
    echo "---"
done
```

## Example Scenarios

### Scenario 1: Setting Up Multi-Provider Embeddings
```python
# 1. Configure OpenAI provider
import os
os.environ['EMBED_PROVIDER'] = 'openai'
os.environ['EMBEDDING_DIM'] = '1536'
os.environ['OPENAI_API_KEY'] = 'your-key'

from core.embeddings.embedder import EmbeddingService
service = EmbeddingService()

# 2. Process some text
text = "Machine learning model for sentiment analysis"
chunks = service._split_text(text)
embeddings = [service._embed_text(chunk) for chunk in chunks]

# 3. Switch to Gemini
os.environ['EMBED_PROVIDER'] = 'gemini'
os.environ['EMBEDDING_DIM'] = '768'
os.environ['GEMINI_API_KEY'] = 'your-key'

# 4. Reinitialize service
service = EmbeddingService()
gemini_embeddings = [service._embed_text(chunk) for chunk in chunks]

print(f"OpenAI dims: {len(embeddings[0])}")
print(f"Gemini dims: {len(gemini_embeddings[0])}")
```

### Scenario 2: Comprehensive Search Testing
```python
from core.search.engine import HybridSearchEngine

# Initialize search engine
search_engine = HybridSearchEngine()

# Test different search types
queries = [
    "transformer model architecture",
    "data preprocessing pipeline", 
    "model evaluation metrics",
    "training configuration"
]

for query in queries:
    print(f"\nSearching: '{query}'")
    
    # Vector search only
    vector_results = search_engine._vector_search(1, query, 5)
    print(f"Vector results: {len(vector_results)}")
    
    # Keyword search only  
    keyword_results = search_engine._keyword_search(1, query, 5)
    print(f"Keyword results: {len(keyword_results)}")
    
    # Hybrid search (combined)
    hybrid_results = search_engine.search(1, query, 5)
    print(f"Hybrid results: {len(hybrid_results)}")
```

### Scenario 3: HuggingFace Batch Processing
```python
from core.scan_hf.fetcher import HuggingFaceFetcher

# Initialize with custom cache settings
fetcher = HuggingFaceFetcher(cache_ttl_hours=12)

# Batch fetch popular models
models = [
    "bert-base-uncased",
    "gpt2", 
    "distilbert-base-uncased",
    "roberta-base",
    "microsoft/DialoGPT-medium"
]

# Fetch all cards
results = fetcher.batch_fetch_cards(models)

# Analyze results
for slug, card in results.items():
    print(f"{slug}:")
    print(f"  Type: {card.type}")
    print(f"  License: {card.license}")
    print(f"  Pipeline: {card.pipeline_tag}")
    print(f"  Tags: {', '.join(card.tags[:3])}...")

# Check cache efficiency
stats = fetcher.get_cache_stats()
print(f"\nCache stats: {stats}")
```

## Advanced Usage Patterns

### Custom Embedding Pipeline
```python
from core.embeddings.embedder import EmbeddingService
from core.schemas.models import EvidenceChunk, RefType

class CustomEmbeddingPipeline:
    def __init__(self):
        self.service = EmbeddingService()
    
    def process_documents(self, documents, project_id):
        all_chunks = []
        
        for doc_path, content in documents.items():
            # Determine reference type
            ref_type = self.service._determine_ref_type(doc_path)
            
            # Split into chunks
            chunks = self.service._split_text(content)
            
            # Create evidence chunks
            for i, chunk_text in enumerate(chunks):
                chunk = EvidenceChunk(
                    project_id=project_id,
                    ref_type=ref_type,
                    ref_path=doc_path,
                    chunk_ix=i,
                    text=chunk_text,
                    token_count=len(self.service.encoding.encode(chunk_text))
                )
                all_chunks.append(chunk)
        
        return all_chunks
```

### Search Result Analysis
```python
from core.search.engine import HybridSearchEngine
import json

def analyze_search_results(query, project_id=1):
    search_engine = HybridSearchEngine()
    
    # Get results from different search methods
    vector_results = search_engine._vector_search(project_id, query, 10)
    keyword_results = search_engine._keyword_search(project_id, query, 10)
    hybrid_results = search_engine.search(project_id, query, 10)
    
    # Analyze overlap and differences
    vector_ids = {r.id for r in vector_results}
    keyword_ids = {r.id for r in keyword_results}
    hybrid_ids = {r.id for r in hybrid_results}
    
    overlap = vector_ids & keyword_ids
    vector_only = vector_ids - keyword_ids
    keyword_only = keyword_ids - vector_ids
    
    analysis = {
        "query": query,
        "vector_count": len(vector_results),
        "keyword_count": len(keyword_results),
        "hybrid_count": len(hybrid_results),
        "overlap_count": len(overlap),
        "vector_only_count": len(vector_only),
        "keyword_only_count": len(keyword_only),
        "fusion_effectiveness": len(hybrid_results) / max(len(vector_results), len(keyword_results), 1)
    }
    
    return analysis
```

## Troubleshooting Examples

### Debug Embedding Issues
```python
from core.embeddings.embedder import EmbeddingService

def debug_embedding_setup():
    try:
        service = EmbeddingService()
        
        # Check provider configuration
        print(f"Provider: {service.provider}")
        print(f"Model: {service.model}")
        print(f"Dimensions: {service.dimensions}")
        print(f"Client available: {service.client is not None}")
        
        # Test embedding generation
        test_text = "This is a test sentence for embedding."
        embedding = service._embed_text(test_text)
        print(f"Test embedding: {len(embedding)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"Embedding setup failed: {e}")
        return False
```

### Validate Search Capabilities
```python
from core.search.engine import HybridSearchEngine

def validate_search_setup():
    search_engine = HybridSearchEngine()
    capabilities = search_engine.get_search_capabilities()
    
    print("Search Capabilities:")
    print(json.dumps(capabilities, indent=2))
    
    # Test each search method
    test_query = "test query"
    project_id = 1
    
    try:
        vector_results = search_engine._vector_search(project_id, test_query, 1)
        print(f"✅ Vector search: {len(vector_results)} results")
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
    
    try:
        keyword_results = search_engine._keyword_search(project_id, test_query, 1)
        print(f"✅ Keyword search: {len(keyword_results)} results")
    except Exception as e:
        print(f"❌ Keyword search failed: {e}")
```

## Best Practices from Examples

### Error Handling
- Always wrap external API calls in try-catch blocks
- Provide meaningful error messages and context
- Implement graceful degradation when services are unavailable
- Log errors with appropriate detail levels

### Performance Optimization
- Use batch processing for multiple operations
- Implement caching for expensive operations
- Monitor memory usage with large datasets
- Use appropriate timeout values

### Configuration Management
- Validate configuration before using services
- Provide clear error messages for missing configuration
- Support multiple configuration sources (env vars, files)
- Document all configuration options

### Testing and Validation
- Include validation steps in examples
- Test both success and failure scenarios
- Provide clear output and status indicators
- Include performance benchmarks where relevant