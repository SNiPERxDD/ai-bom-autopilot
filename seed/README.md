# Seed Data and Demo Projects

This directory contains demo data, sample projects, and scripts for testing and demonstration purposes.

## Contents

### 🎯 Demo Scripts
- **`create_demo_project.py`** - Creates a demo project with sample ML artifacts
- **`apply_demo_changes.py`** - Applies scripted changes to trigger policy events
- **`test_seed_data.py`** - Validates seed data integrity and structure

### 📁 Sample Project (`sample_project/`)
A complete ML project structure with various AI/ML artifacts for testing:

#### Project Structure
```
sample_project/
├── README.md                    # Project documentation
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── config.yaml                 # Application configuration
├── Dockerfile                  # Container configuration
├── .gitignore                  # Git ignore patterns
├── train.py                    # Training script
├── evaluation.py               # Model evaluation
├── data_processing.py          # Data preprocessing
├── notebook.ipynb              # Jupyter notebook
├── models/
│   └── model_config.json       # Model configuration
├── datasets/
│   └── dataset_manifest.yaml   # Dataset metadata
├── prompts/
│   ├── system_prompt.txt       # System prompts
│   ├── classification_prompt.txt
│   └── qa_prompt.txt
└── tools/
    ├── model_utils.py          # Utility functions
    └── requirements.txt        # Tool dependencies
```

#### Artifact Types Included
- **Models**: Configuration files, training scripts
- **Datasets**: Manifest files, preprocessing scripts
- **Prompts**: System prompts, task-specific prompts
- **Tools**: Utility scripts, helper functions
- **Documentation**: README, configuration files

## Demo Workflow

### 1. Initial Setup
```bash
# Create demo project in database
python seed/create_demo_project.py
```

This script:
- Creates a "demo" project entry in the database
- Initializes the sample project structure
- Populates initial metadata
- Prepares for first scan

### 2. First Scan (Baseline)
```bash
# Run initial scan to create BOM v1
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"project": "demo"}'
```

Expected results:
- **Models**: 3 detected (training, inference, evaluation)
- **Datasets**: 2 detected (training, validation)
- **Prompts**: 5 detected (system, classification, QA)
- **Tools**: 1 detected (model utilities)
- **BOM**: CycloneDX ML-BOM v1 generated
- **Policy Events**: None (clean baseline)

### 3. Apply Changes
```bash
# Apply scripted changes to trigger policy events
python seed/apply_demo_changes.py
```

This script applies:
- **Model Version Bump**: 8B → 70B parameter model
- **License Change**: MIT → GPL-3.0 (potential violation)
- **Prompt Modification**: Changes to protected system prompt
- **New Dependencies**: Adds new tool dependencies

### 4. Second Scan (Change Detection)
```bash
# Run second scan to detect changes
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"project": "demo"}'
```

Expected results:
- **BOM**: CycloneDX ML-BOM v2 generated
- **Diff**: Structural changes detected and stored
- **Policy Events**: 
  - Major model version bump (medium severity)
  - License change to GPL-3.0 (high severity)
  - Protected prompt modification (high severity)
- **Notifications**: Slack alert and Jira ticket created

## Sample Artifacts

### Model Configuration (`models/model_config.json`)
```json
{
  "name": "text-classifier",
  "version": "1.0.0",
  "architecture": "transformer",
  "parameters": "8B",
  "provider": "huggingface",
  "license": "MIT",
  "description": "Text classification model for sentiment analysis"
}
```

### Dataset Manifest (`datasets/dataset_manifest.yaml`)
```yaml
name: sentiment-dataset
version: "2.1.0"
provider: "internal"
license: "CC-BY-4.0"
description: "Curated sentiment analysis dataset"
splits:
  train: 10000
  validation: 2000
  test: 1000
```

### System Prompt (`prompts/system_prompt.txt`)
```
You are a helpful AI assistant specialized in text classification.
Analyze the given text and provide accurate sentiment predictions.
Always explain your reasoning and confidence level.
```

### Training Script (`train.py`)
```python
#!/usr/bin/env python3
"""
Model training script for sentiment classification
"""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def train_model():
    # Model training logic
    model_name = "bert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    # ... training code ...
```

## Testing and Validation

### Seed Data Validation
```bash
# Validate seed data integrity
python seed/test_seed_data.py
```

This test verifies:
- All required files exist
- JSON/YAML files are valid
- Configuration consistency
- Artifact metadata completeness

### Demo Workflow Testing
```bash
# Run complete demo workflow
python seed/create_demo_project.py
python -c "
import requests
response = requests.post('http://localhost:8000/scan', 
                        json={'project': 'demo'})
print(f'Scan 1: {response.status_code}')
"
python seed/apply_demo_changes.py
python -c "
import requests
response = requests.post('http://localhost:8000/scan', 
                        json={'project': 'demo'})
print(f'Scan 2: {response.status_code}')
"
```

## Customization

### Creating New Demo Projects
1. **Copy Sample Structure**: Use `sample_project/` as template
2. **Modify Artifacts**: Update configurations and metadata
3. **Update Scripts**: Modify `create_demo_project.py` for new project
4. **Test Changes**: Run validation scripts

### Adding New Artifact Types
1. **Create Sample Files**: Add new file types to sample project
2. **Update Classifier**: Modify normalization logic if needed
3. **Update Policies**: Add new policy rules for artifact type
4. **Test Detection**: Verify artifacts are properly classified

### Custom Policy Scenarios
1. **Define Violations**: Identify specific policy violations to test
2. **Create Changes**: Script changes that trigger violations
3. **Update Demo Script**: Modify `apply_demo_changes.py`
4. **Verify Detection**: Ensure policy engine catches violations

## File Formats Supported

### Configuration Files
- **JSON**: Model configs, tool manifests
- **YAML**: Dataset manifests, application configs
- **TOML**: Project configuration (pyproject.toml)

### Code Files
- **Python**: Training scripts, utilities (.py)
- **Jupyter**: Notebooks (.ipynb)
- **Docker**: Container definitions (Dockerfile)

### Documentation
- **Markdown**: README files, documentation (.md)
- **Text**: Prompts, templates (.txt, .prompt)

### Dependencies
- **Requirements**: Python packages (requirements.txt)
- **Lock Files**: Dependency locks (poetry.lock, Pipfile.lock)

## Best Practices

### Demo Project Design
- **Realistic Structure**: Mirror real ML project layouts
- **Diverse Artifacts**: Include all supported artifact types
- **Clear Metadata**: Provide complete and accurate metadata
- **Version Consistency**: Ensure version numbers are realistic

### Change Scenarios
- **Meaningful Changes**: Apply changes that would occur in real projects
- **Policy Triggers**: Ensure changes trigger relevant policy rules
- **Gradual Evolution**: Show realistic project evolution patterns
- **Documentation**: Document why changes were made

### Testing Approach
- **Automated Validation**: Scripts to verify demo integrity
- **End-to-End Testing**: Complete workflow validation
- **Error Scenarios**: Test failure cases and recovery
- **Performance Testing**: Measure scan times and resource usage