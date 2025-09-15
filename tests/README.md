# Test Suite

This directory contains the comprehensive test suite for AI-BOM Autopilot.

## Test Categories

### 🔧 Setup and Infrastructure Tests
- **`test_setup.py`** - Dependency installation and basic setup validation
- **`test_migrations.py`** - Database migration testing
- **`test_migration_structure.py`** - Migration structure validation

### 🏥 Health and Capabilities Tests
- **`test_selftest_mock.py`** - System self-test with mocking
- **`test_sql_syntax.py`** - SQL syntax and API structure validation

### 🔄 Workflow and Integration Tests
- **`test_e2e_mock.py`** - End-to-end mock workflow testing
- **`test_workflow_integration.py`** - LangGraph workflow integration
- **`test_api_workflow.py`** - API and workflow integration
- **`test_api_mock.py`** - API endpoint mocking and validation

### 🧠 Core Component Tests
- **`test_embeddings.py`** - Embedding service unit tests
- **`test_embeddings_integration.py`** - Embedding integration tests
- **`test_embedding_integration.py`** - Cross-component embedding tests
- **`test_embedding_providers.py`** - Multi-provider embedding tests

### 🔍 Search and Retrieval Tests
- **`test_hybrid_search.py`** - Hybrid search engine unit tests
- **`test_hybrid_search_integration.py`** - Search integration tests

### 📊 BOM and Policy Tests
- **`test_bom_generator.py`** - BOM generation unit tests
- **`test_diff_engine.py`** - BOM diff engine tests
- **`test_policy_engine.py`** - Policy evaluation tests
- **`test_bom_diff_policy_integration.py`** - Integrated BOM/diff/policy tests

### 🏷️ Classification and Scanning Tests
- **`test_normalize_classifier.py`** - Artifact classification tests
- **`test_normalize_integration.py`** - Classification integration tests
- **`test_scan_hf.py`** - HuggingFace scanner unit tests
- **`test_scan_hf_integration.py`** - HF scanner integration tests

### 🔗 External Integration Tests
- **`test_slack_notifier.py`** - Slack notification tests
- **`test_jira_notifier.py`** - Jira integration tests
- **`test_action_logging.py`** - External action logging tests

### 🗄️ Database and Migration Tests
- **`test_vector_migration.py`** - Vector column migration tests
- **`test_task_5_1_complete.py`** - Task 5.1 completion verification

### 🖥️ User Interface Tests
- **`test_ui.py`** - Streamlit UI functionality tests

### ✅ Verification and Validation Tests
- **`verify_setup.py`** - System setup verification
- **`verify_task_6_1_complete.py`** - Task 6.1 completion verification

## Test Execution

### Run All Tests
```bash
# Comprehensive test suite
python run_all_tests.py

# Individual test categories
python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Setup and infrastructure
python tests/test_setup.py
python tests/test_migrations.py

# Core functionality
python tests/test_embeddings.py
python tests/test_bom_generator.py
python tests/test_policy_engine.py

# Integration tests
python tests/test_e2e_mock.py
python tests/test_workflow_integration.py

# External integrations
python tests/test_slack_notifier.py
python tests/test_jira_notifier.py
```

### Run Tests with Coverage
```bash
# Install coverage tools
pip install pytest-cov coverage

# Run with coverage reporting
python -m pytest tests/ --cov=core --cov-report=html --cov-report=term
```

## Test Architecture

### Mocking Strategy
```python
# Database mocking
@patch('core.db.connection.db_manager')
def test_with_mock_db(mock_db):
    mock_db.capabilities = {'vector': True, 'fulltext': False}
    # Test logic here

# API mocking
@patch('requests.post')
def test_external_api(mock_post):
    mock_post.return_value.status_code = 200
    # Test logic here
```

### Test Data Management
```python
# Fixture-based test data
@pytest.fixture
def sample_artifacts():
    return [
        Model(name="test-model", version="1.0.0"),
        Dataset(name="test-dataset", version="2.0.0")
    ]

# Temporary database for integration tests
@pytest.fixture
def temp_db():
    # Setup temporary database
    yield db_connection
    # Cleanup
```

### Error Scenario Testing
```python
# Test error handling
def test_network_failure():
    with patch('requests.get', side_effect=ConnectionError):
        result = service.fetch_data()
        assert result is None
        assert "connection error" in caplog.text
```

## Test Configuration

### Environment Variables for Testing
```bash
# Test database (optional)
TEST_DB_URL=sqlite:///test.db

# Mock external services
MOCK_EXTERNAL_APIS=true

# Test-specific settings
LOG_LEVEL=DEBUG
DRY_RUN=true
```

### Test Settings (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    external: Tests requiring external services
```

## Test Categories by Complexity

### Unit Tests (Fast, Isolated)
- Individual function/method testing
- No external dependencies
- Extensive mocking
- Quick feedback loop

**Examples:**
- `test_embeddings.py` - Embedding service methods
- `test_bom_generator.py` - BOM generation logic
- `test_policy_engine.py` - Policy rule evaluation

### Integration Tests (Medium, Cross-Component)
- Multiple component interaction
- Limited external dependencies
- Database integration (mocked or temporary)
- Realistic data flow

**Examples:**
- `test_workflow_integration.py` - LangGraph workflow
- `test_hybrid_search_integration.py` - Search with embeddings
- `test_bom_diff_policy_integration.py` - BOM → Diff → Policy flow

### End-to-End Tests (Slow, Full System)
- Complete workflow testing
- Real or realistic external services
- Full database integration
- Production-like scenarios

**Examples:**
- `test_e2e_mock.py` - Complete scan workflow
- `test_api_workflow.py` - API → Workflow → Response

## Test Data and Fixtures

### Sample Data Structure
```python
# Standard test artifacts
TEST_MODELS = [
    {
        "name": "test-classifier",
        "version": "1.0.0",
        "provider": "huggingface",
        "license": "MIT"
    }
]

TEST_DATASETS = [
    {
        "name": "sentiment-data",
        "version": "2.1.0",
        "provider": "internal",
        "license": "CC-BY-4.0"
    }
]
```

### Mock Responses
```python
# HuggingFace API mock response
HF_MODEL_RESPONSE = {
    "id": "bert-base-uncased",
    "pipeline_tag": "text-classification",
    "tags": ["pytorch", "bert"],
    "license": "apache-2.0"
}

# Slack webhook mock response
SLACK_SUCCESS_RESPONSE = {
    "ok": True,
    "message": "Message sent successfully"
}
```

## Performance Testing

### Load Testing
```python
# Concurrent scan testing
def test_concurrent_scans():
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(trigger_scan, f"project-{i}")
            for i in range(10)
        ]
        results = [f.result() for f in futures]
    assert all(r.success for r in results)
```

### Memory Testing
```python
# Memory usage monitoring
def test_memory_usage():
    import psutil
    process = psutil.Process()
    
    initial_memory = process.memory_info().rss
    
    # Run memory-intensive operation
    large_scan_result = process_large_repository()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Assert reasonable memory usage
    assert memory_increase < 100 * 1024 * 1024  # 100MB limit
```

## Continuous Integration

### GitHub Actions Integration
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python run_all_tests.py
```

### Test Reporting
- **Coverage Reports**: HTML and terminal coverage reports
- **Test Results**: JUnit XML for CI integration
- **Performance Metrics**: Test execution time tracking
- **Failure Analysis**: Detailed error reporting and stack traces

## Best Practices

### Test Design
- **Arrange-Act-Assert**: Clear test structure
- **Single Responsibility**: One concept per test
- **Descriptive Names**: Clear test purpose from name
- **Independent Tests**: No test dependencies

### Mocking Guidelines
- **Mock External Dependencies**: APIs, databases, file systems
- **Preserve Interfaces**: Mock at service boundaries
- **Realistic Responses**: Use production-like mock data
- **Error Scenarios**: Test failure cases

### Test Maintenance
- **Regular Updates**: Keep tests current with code changes
- **Cleanup**: Remove obsolete tests
- **Documentation**: Comment complex test logic
- **Refactoring**: Extract common test utilities

### Performance Considerations
- **Fast Unit Tests**: Keep unit tests under 1 second
- **Parallel Execution**: Use pytest-xdist for parallel testing
- **Resource Cleanup**: Properly clean up test resources
- **Test Isolation**: Prevent test interference