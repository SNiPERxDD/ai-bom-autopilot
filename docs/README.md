# Documentation

This directory contains detailed documentation for AI-BOM Autopilot implementation and usage.

## Documentation Overview

### 📋 Implementation Documentation
- **`TASK_5_1_VERIFICATION.md`** - BOM generation, diff engine, and policy engine implementation verification
- **`TASK_7_1_IMPLEMENTATION.md`** - LangGraph workflow and FastAPI endpoint implementation summary
- **`HYBRID_SEARCH_IMPLEMENTATION.md`** - Hybrid search engine implementation with VEC_COSINE_DISTANCE queries

### 🧠 Embedding and Search Documentation
- **`EMBEDDING_PROVIDERS.md`** - Multi-provider embedding support (OpenAI/Gemini)
- **`EMBEDDING_SERVICE.md`** - Comprehensive embedding service documentation
- **`VECTOR_MIGRATION.md`** - Vector column migration procedures and examples

### 🗄️ Database Documentation
- **`MIGRATIONS.md`** - Database schema migrations and management

### 🎯 Demo and Validation Documentation
- **`DEMO.md`** - Demo workflow and usage instructions
- **`VALIDATION_REPORT.md`** - System validation and testing reports

## Quick Reference

### Key Implementation Features

#### ✅ BOM Generation (Task 5.1)
- CycloneDX ML-BOM v1.5 generation using cyclonedx-python-lib
- SHA256 hash calculation and validation
- Structural diff engine with stable component IDs
- Policy engine with 5 starter policies and deduplication logic

#### ✅ Workflow Orchestration (Task 7.1)
- Complete LangGraph DAG: ScanPlan → ScanGit → ScanHF → Normalize → Embed+Index → BOMGen → DiffPrev → PolicyCheck → Notify → End
- Timeout protection and retry logic for all nodes
- FastAPI endpoint POST /scan with comprehensive response format
- DRY_RUN mode support and tool allowlist enforcement

#### ✅ Hybrid Search (Task 4.4)
- VEC_COSINE_DISTANCE queries for vector similarity search
- MATCH(...) AGAINST(...) for FULLTEXT search with BM25 fallback
- Reciprocal Rank Fusion (RRF) algorithm for result combination
- Graceful degradation when vector/FULLTEXT features unavailable

### Multi-Provider Embedding Support

#### OpenAI Configuration
```bash
EMBED_PROVIDER=openai
EMBEDDING_DIM=1536
OPENAI_API_KEY=sk-your-key
EMBEDDING_MODEL=text-embedding-3-small
```

#### Gemini Configuration
```bash
EMBED_PROVIDER=gemini
EMBEDDING_DIM=768
GEMINI_API_KEY=your-key
EMBEDDING_MODEL=models/embedding-001
```

#### Provider Switching
1. Update environment variables
2. Run vector migration: `python -m core.db.migrations resize-vector`
3. Restart application

### Database Migrations

#### Available Migrations
- **`up`** - Apply all pending migrations
- **`down`** - Rollback last migration
- **`status`** - Show migration status
- **`resize-vector`** - Resize vector column dimensions

#### Migration Commands
```bash
# Apply migrations
python -m core.db.migrations up

# Check status
python -m core.db.migrations status

# Resize vector column for provider switch
python -m core.db.migrations resize-vector --dimension 768
```

### System Capabilities

#### Database Features
- **Vector Functions**: TiDB VEC_COSINE_DISTANCE support detection
- **Full-text Search**: MATCH(...) AGAINST(...) availability check
- **Fallback Search**: BM25 and LIKE search alternatives
- **Migration System**: Automated schema updates

#### Search Capabilities
- **Vector Search**: Semantic similarity using embeddings
- **Keyword Search**: FULLTEXT or BM25 fallback
- **Hybrid Fusion**: RRF combination of vector and keyword results
- **Graceful Degradation**: Automatic fallback chain

#### Policy Engine
- **5 Starter Policies**: License violations, model drift, prompt changes
- **Severity Levels**: Low, medium, high, critical
- **Deduplication**: 24-hour window with MD5 dedupe keys
- **Override Support**: Temporary waivers with expiration

## Architecture Documentation

### System Architecture
```mermaid
graph TD
    A[Git Repository] --> B[ScanGit]
    C[HuggingFace] --> D[ScanHF]
    B --> E[Normalize]
    D --> E
    E --> F[Embed+Index]
    F --> G[BOMGen]
    G --> H[DiffPrev]
    H --> I[PolicyCheck]
    I --> J[Notify]
    
    K[TiDB Serverless] <--> F
    K <--> G
    K <--> H
    K <--> I
    
    L[Slack] <-- J
    M[Jira] <-- J
```

### Data Flow
1. **Discovery**: Scan Git repos and HuggingFace for ML artifacts
2. **Classification**: Normalize and classify artifacts with SPDX licenses
3. **Indexing**: Generate embeddings and store in vector database
4. **BOM Generation**: Create CycloneDX ML-BOM with validation
5. **Change Detection**: Compare BOMs using structural diffs
6. **Policy Evaluation**: Check compliance rules and generate events
7. **Notification**: Send alerts via Slack/Jira with audit logging

### Component Integration
- **LangGraph Orchestration**: Stateful workflow with timeout/retry
- **Multi-Provider Embeddings**: OpenAI/Gemini with dimension handling
- **Hybrid Search**: Vector + keyword search with RRF fusion
- **Policy Engine**: Configurable rules with deduplication
- **External Integrations**: Slack webhooks and Jira REST API

## Usage Documentation

### Quick Start
```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with credentials

# 2. Install and test
pip install -r requirements.txt
python run_all_tests.py

# 3. Initialize database
python -m core.db.migrations up

# 4. Start services
./run.sh

# 5. Run demo
python seed/create_demo_project.py
curl -X POST http://localhost:8000/scan -d '{"project":"demo"}'
```

### API Usage
```bash
# Trigger scan
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"project": "demo", "dry_run": false}'

# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

### UI Access
- **Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Troubleshooting Documentation

### Common Issues

#### "No embedding client available"
- **Cause**: Missing or invalid API keys
- **Solution**: Check OPENAI_API_KEY or GEMINI_API_KEY in .env
- **Verification**: Run `python core/graph/selftest.py`

#### "Vector functions not available"
- **Cause**: TiDB cluster doesn't support vector functions
- **Impact**: System continues with keyword-only search
- **Solution**: Upgrade TiDB plan or use different cluster region

#### "FTS disabled -> BM25(app)"
- **Cause**: TiDB region doesn't support FULLTEXT search
- **Impact**: Automatic fallback to BM25 library
- **Solution**: No action needed, system continues normally

#### Database connection errors
- **Cause**: Invalid TiDB credentials or network issues
- **Solution**: Verify TIDB_URL, DB_USER, DB_PASS in .env
- **Debug**: Check network connectivity and database existence

### Debug Commands
```bash
# System self-test
python core/graph/selftest.py

# Database status
python -m core.db.migrations status

# Test individual components
python examples/example_embeddings_usage.py
python examples/example_hybrid_search_usage.py

# Enable debug logging
LOG_LEVEL=DEBUG ./run.sh
```

## Performance Documentation

### Benchmarks
- **Throughput**: ~120 chunks/sec with 8 workers
- **Storage**: ~6KB per vector chunk
- **Latency**: <100ms for hybrid search queries
- **Scalability**: Horizontal scaling with stateless services

### Optimization Guidelines
- **Batch Processing**: Use appropriate batch sizes for embeddings
- **Connection Pooling**: Configure database connection limits
- **Caching**: Enable TTL caching for HuggingFace API responses
- **Indexing**: Ensure proper vector and FULLTEXT indexes

### Resource Requirements
- **Memory**: 2GB minimum, 4GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended
- **Storage**: 10GB for database, 1GB for application
- **Network**: Stable internet for API calls

## Security Documentation

### Security Features
- **Input Validation**: Comprehensive sanitization using Pydantic
- **SQL Injection Prevention**: Parameterized queries only
- **Secrets Management**: Environment variables, no hardcoded keys
- **Audit Logging**: All external actions logged with payloads
- **Tool Allowlist**: Only approved notification channels

### Best Practices
- **API Keys**: Rotate regularly, use least-privilege access
- **Database**: Use strong passwords, enable SSL/TLS
- **Network**: Firewall rules, VPN for production access
- **Monitoring**: Log analysis, anomaly detection

### Compliance
- **GDPR**: No PII storage, configurable data retention
- **SOC 2**: Audit logging, access controls
- **EU AI Act**: CycloneDX ML-BOM for transparency
- **NIST**: Security framework alignment

## Contributing Documentation

### Development Setup
1. Fork repository and create feature branch
2. Install development dependencies
3. Run test suite to ensure baseline
4. Make changes with appropriate tests
5. Update documentation as needed
6. Submit pull request with clear description

### Code Standards
- **Python**: Follow PEP 8, use type hints
- **Testing**: Maintain >90% test coverage
- **Documentation**: Update docstrings and README files
- **Commits**: Use conventional commit messages

### Review Process
- **Automated**: CI/CD pipeline runs all tests
- **Manual**: Code review for logic and style
- **Documentation**: Verify documentation updates
- **Integration**: Test with existing components