# ML Model Detection and Repository Organization

This document explains how AI-BOM Autopilot detects machine learning models and handles repository organization.

## ML/DL Model Detection

AI-BOM Autopilot scans repositories to identify various types of machine learning components:

### How Model Detection Works

The system detects ML models through several mechanisms:

1. **Static Code Analysis**:
   - Scans Python files for imports and patterns indicative of ML frameworks
   - Recognizes popular frameworks like TensorFlow, PyTorch, XGBoost, scikit-learn, etc.
   - Identifies common model architectures like autoencoders, CNNs, transformers, etc.

2. **Runtime Detection**:
   - Monitors running Python processes for ML library usage
   - Captures model loading and inference operations
   - Detects models loaded from files or downloaded from remote sources

3. **HuggingFace Integration**:
   - Directly identifies models referenced from HuggingFace Hub
   - Extracts metadata from model cards and configuration files

### Supported ML Frameworks

The system can detect:
- XGBoost models (gradient boosting)
- Autoencoder architectures
- TensorFlow/Keras models
- PyTorch models
- scikit-learn models
- LightGBM models
- Hugging Face transformers
- And many more!

## Repository Organization

### Repository Cloning

When scanning a repository:

1. Repositories are cloned into a dedicated `repos/` directory
2. Each repo gets a unique subdirectory named `id=X_ProjectName`
3. The `repos/` directory is included in `.gitignore` to prevent accidental commits

### Runtime Scanning Process

The runtime scanning process works as follows:

1. The system starts a monitoring process that watches for ML operations
2. You need to run your ML application during the 30-second collection window
3. The system captures information about loaded models, datasets, and other artifacts
4. This information is combined with static analysis to create a complete inventory

### Best Practices

- Use the `./cleanup.sh` script to kill any lingering processes
- Run `./monitor_scan.py` to see real-time progress of your scans
- If you're not seeing expected models, try running the application during the scan window

## Additional Notes

- No LLM API key (OpenAI/Gemini) is required for basic functionality
- Detection is primarily rule-based, not LLM-based
- The system stores extracted information in a MySQL database
- Generated BOMs follow the CycloneDX standard
