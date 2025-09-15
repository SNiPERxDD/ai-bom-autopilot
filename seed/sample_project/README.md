# Sample ML Project

This is a comprehensive sample machine learning project designed for testing the AI-BOM Autopilot system. It demonstrates a realistic ML workflow with multiple models, datasets, prompts, and tools.

## Project Overview

This project implements a multi-model AI system for text processing tasks including:
- Sentiment analysis using BERT
- Text generation using LLaMA
- Embeddings generation using Sentence Transformers
- Advanced reasoning using OpenAI GPT-4

## AI/ML Assets

### Models

- **LLaMA 3.1 8B** (`meta-llama/Llama-3.1-8B`)
  - Provider: Hugging Face
  - License: Custom (Llama 2 Community License)
  - Use Case: Text generation and completion
  - Parameters: 8 billion

- **BERT Base Uncased** (`bert-base-uncased`)
  - Provider: Hugging Face  
  - License: Apache-2.0
  - Use Case: Text classification and sentiment analysis
  - Parameters: 110 million

- **Sentence Transformers** (`sentence-transformers/all-MiniLM-L6-v2`)
  - Provider: Hugging Face
  - License: Apache-2.0
  - Use Case: Semantic embeddings and similarity
  - Parameters: 22 million

- **OpenAI GPT-4** (`gpt-4`)
  - Provider: OpenAI
  - License: Proprietary
  - Use Case: Advanced reasoning and data augmentation
  - Parameters: Unknown

### Datasets

- **IMDB Movie Reviews** (`imdb`)
  - License: Apache-2.0
  - Type: Text classification
  - Size: 25,000 samples
  - Use Case: Sentiment analysis training

- **SQuAD** (`squad`)
  - License: CC BY-SA 4.0
  - Type: Question answering
  - Size: 100k+ samples
  - Use Case: Reading comprehension

- **WikiText-103** (`wikitext-103-raw-v1`)
  - License: CC BY-SA 3.0
  - Type: Language modeling
  - Size: 103M tokens
  - Use Case: Language model pretraining

### Prompts

- **System Prompt** (`prompts/system_prompt.txt`)
  - Type: System configuration
  - Protected: Yes
  - Purpose: AI assistant behavior definition

- **Classification Prompt** (`prompts/classification_prompt.txt`)
  - Type: Task-specific
  - Protected: No
  - Purpose: Sentiment classification instructions

- **QA Prompt** (`prompts/qa_prompt.txt`)
  - Type: Task-specific
  - Protected: Yes
  - Purpose: Question answering format

### Tools and Dependencies

- **Core ML Frameworks**
  - PyTorch 2.1.0 (BSD-3-Clause)
  - Transformers 4.35.0 (Apache-2.0)
  - Datasets 2.14.0 (Apache-2.0)
  - Sentence Transformers 2.2.2 (Apache-2.0)

- **API Clients**
  - OpenAI 1.3.0 (MIT)
  - Anthropic 0.7.0 (MIT)

- **Data Processing**
  - NumPy 1.24.3 (BSD-3-Clause)
  - Pandas 2.0.3 (BSD-3-Clause)
  - Scikit-learn 1.3.0 (BSD-3-Clause)

## Setup and Installation

### Prerequisites

- Python 3.8+
- CUDA-capable GPU (optional, for local model inference)
- OpenAI API key (for GPT-4 usage)

### Installation

```bash
# Clone or navigate to project directory
cd sample-ml-project

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_key_here

# Hugging Face (optional, for private models)
HF_TOKEN=your_hf_token_here

# Model cache directory
TRANSFORMERS_CACHE=./cache/transformers
HF_HOME=./cache/huggingface
```

## Usage

### Training Pipeline

```bash
# Run the complete training pipeline
python train.py
```

This will:
1. Load all configured models
2. Process datasets (IMDB, SQuAD)
3. Generate embeddings
4. Run classification training
5. Test OpenAI integration

### Data Processing

```bash
# Run data preprocessing
python data_processing.py
```

### Model Evaluation

```bash
# Run comprehensive evaluation
python evaluation.py
```

### Jupyter Notebook

```bash
# Start Jupyter and open notebook.ipynb
jupyter notebook
```

## Project Structure

```
sample-ml-project/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Container setup
├── config.yaml                 # ML configuration
├── train.py                    # Main training script
├── data_processing.py          # Data pipeline
├── evaluation.py               # Model evaluation
├── notebook.ipynb             # Jupyter notebook
├── models/
│   └── model_config.json       # Model configurations
├── datasets/
│   └── dataset_manifest.yaml   # Dataset metadata
├── prompts/
│   ├── system_prompt.txt       # System prompt
│   ├── classification_prompt.txt # Classification prompt
│   └── qa_prompt.txt           # QA prompt
└── tools/
    ├── requirements.txt        # Tool-specific deps
    └── model_utils.py          # Utility functions
```

## Docker Usage

```bash
# Build container
docker build -t sample-ml-project .

# Run training
docker run --rm -v $(pwd):/app sample-ml-project

# Run with GPU support
docker run --rm --gpus all -v $(pwd):/app sample-ml-project
```

## Development

### Code Quality

```bash
# Format code
black .

# Lint code  
flake8 .

# Type checking
mypy .

# Run tests
pytest
```

### Adding New Models

1. Update `models/model_config.json`
2. Add loading logic in `train.py`
3. Update documentation

### Adding New Datasets

1. Update `datasets/dataset_manifest.yaml`
2. Add processing logic in `data_processing.py`
3. Update training pipeline

## AI-BOM Autopilot Integration

This project is designed to work with AI-BOM Autopilot for:

- **Asset Discovery**: Automatic detection of models, datasets, prompts, tools
- **License Compliance**: Tracking of all component licenses
- **Version Management**: Monitoring changes and upgrades
- **Policy Enforcement**: Detecting violations and drift

### Expected BOM Components

When scanned by AI-BOM Autopilot, this project should generate:
- 4 model components (LLaMA, BERT, Sentence Transformers, GPT-4)
- 3 dataset components (IMDB, SQuAD, WikiText)
- 3 prompt components (system, classification, QA)
- 15+ tool components (PyTorch, Transformers, etc.)

## License

This sample project is licensed under MIT License.

Individual components have their own licenses:
- Models: Various (Apache-2.0, Custom, Proprietary)
- Datasets: Various (Apache-2.0, CC BY-SA)
- Tools: Various (Apache-2.0, BSD-3-Clause, MIT)

See individual component documentation for specific license terms.