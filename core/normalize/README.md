# Artifact Normalization and Classification

This module provides enhanced artifact classification and normalization capabilities for ML-BOM Autopilot.

## Features

### 1. Stable Canonical ID Generation
- Generates unique, stable identifiers for all artifacts
- Format: `project:name:kind:provider:version`
- Normalizes special characters to ensure consistency
- Example: `ml_project:llama_2_7b:model:meta:2.0`

### 2. Enhanced License Detection
- **SPDX License Mapping**: Maps common license strings to SPDX identifiers
- **File-based Detection**: Scans file content for license headers and SPDX identifiers
- **Unknown License Flagging**: Identifies and flags proprietary/unknown licenses
- **Pattern Matching**: Detects licenses in various formats (headers, comments, metadata)

### 3. Comprehensive Artifact Classification

#### Models
- Extracts from Hugging Face model cards
- Detects provider based on slug and metadata
- Normalizes version information
- Includes model type, pipeline tags, and library information

#### Datasets
- Processes Hugging Face dataset cards
- Extracts licensing and provenance information
- Handles dataset-specific metadata

#### Prompts
- Detects prompts in multiple formats:
  - Triple-quoted strings (`"""` or `'''`)
  - Variable assignments (`prompt = "..."`)
  - System/user prompt patterns
  - Template definitions
- Generates SHA256 hashes for content deduplication

#### Tools
- **Python Functions**: Detects API handlers, tool functions, class definitions
- **FastAPI Endpoints**: Identifies REST API endpoints with decorators
- **MCP Tools**: Parses JSON-based MCP tool definitions
- **OpenAPI Specs**: Processes OpenAPI/Swagger specifications

### 4. License Detection Capabilities

#### Known License Patterns
- MIT, Apache-2.0, GPL-3.0, BSD-3-Clause
- Creative Commons (CC-BY-4.0, CC-BY-SA-4.0)
- OpenRAIL variants
- SPDX identifier detection

#### Unknown License Handling
- Flags proprietary licenses (llama2, custom, internal)
- Provides warnings for unrecognized licenses
- Maintains original license text for audit purposes

## Usage

```python
from core.normalize.classifier import ArtifactClassifier
from core.schemas.models import ScanState, Project

classifier = ArtifactClassifier()

# Normalize artifacts from scan results
state = ScanState(project=project, commit_sha="abc123")
normalized_state = classifier.normalize_artifacts(state, hf_cards)

# Check for unknown licenses
for model in normalized_state.models:
    if model.meta.get('license_unknown'):
        print(f"Warning: {model.name} has unknown license: {model.license}")
```

## Testing

Run the test suite to verify functionality:

```bash
python test_normalize_classifier.py      # Unit tests
python test_normalize_integration.py     # Integration tests
```

## Requirements Compliance

This implementation satisfies requirement 1.5:
- ✅ Build artifact classification logic for model, dataset, prompt, tool categories
- ✅ Integrate license detection for SPDX license mapping
- ✅ Generate stable, canonical IDs for each artifact
- ✅ Flag unknown licenses appropriately