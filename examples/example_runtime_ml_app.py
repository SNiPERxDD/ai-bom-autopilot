#!/usr/bin/env python3
"""
Example ML application to demonstrate runtime tracing.

This script simulates a typical ML workflow that loads models, datasets,
and prompts, which should be captured by the runtime tracer.
"""

import os
import time
import json
import tempfile
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_artifacts():
    """Create sample AI/ML artifacts for demonstration."""
    
    # Create temporary directory for artifacts
    temp_dir = Path(tempfile.mkdtemp(prefix="ml_demo_"))
    logger.info(f"Creating sample artifacts in: {temp_dir}")
    
    # Create model files
    models_dir = temp_dir / "models"
    models_dir.mkdir()
    
    # Simulate PyTorch model
    model_file = models_dir / "bert-base-uncased.bin"
    with open(model_file, 'wb') as f:
        f.write(b"FAKE_MODEL_DATA" * 1000)  # Fake binary data
    
    # Simulate config file
    config_file = models_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump({
            "model_type": "bert",
            "hidden_size": 768,
            "num_attention_heads": 12,
            "num_hidden_layers": 12
        }, f)
    
    # Create dataset files
    datasets_dir = temp_dir / "datasets"
    datasets_dir.mkdir()
    
    train_file = datasets_dir / "train.csv"
    with open(train_file, 'w') as f:
        f.write("text,label\n")
        f.write("This is a positive example,1\n")
        f.write("This is a negative example,0\n")
    
    # Create prompt files
    prompts_dir = temp_dir / "prompts"
    prompts_dir.mkdir()
    
    system_prompt = prompts_dir / "system_prompt.txt"
    with open(system_prompt, 'w') as f:
        f.write("You are a helpful AI assistant specialized in text classification.")
    
    user_prompt = prompts_dir / "classification_prompt.txt"
    with open(user_prompt, 'w') as f:
        f.write("Please classify the following text as positive or negative: {text}")
    
    return temp_dir

def simulate_model_loading(artifacts_dir):
    """Simulate loading ML models."""
    logger.info("🤖 Loading ML models...")
    
    models_dir = artifacts_dir / "models"
    
    # Simulate loading model binary
    model_file = models_dir / "bert-base-uncased.bin"
    logger.info(f"Loading model from: {model_file}")
    with open(model_file, 'rb') as f:
        model_data = f.read()
        logger.info(f"Loaded model data: {len(model_data)} bytes")
    
    # Simulate loading config
    config_file = models_dir / "config.json"
    logger.info(f"Loading config from: {config_file}")
    with open(config_file, 'r') as f:
        config = json.load(f)
        logger.info(f"Model config: {config}")
    
    time.sleep(1)  # Simulate processing time

def simulate_dataset_loading(artifacts_dir):
    """Simulate loading datasets."""
    logger.info("📊 Loading datasets...")
    
    datasets_dir = artifacts_dir / "datasets"
    
    # Simulate loading training data
    train_file = datasets_dir / "train.csv"
    logger.info(f"Loading training data from: {train_file}")
    with open(train_file, 'r') as f:
        lines = f.readlines()
        logger.info(f"Loaded {len(lines)} training examples")
    
    time.sleep(0.5)  # Simulate processing time

def simulate_prompt_loading(artifacts_dir):
    """Simulate loading prompts."""
    logger.info("💬 Loading prompts...")
    
    prompts_dir = artifacts_dir / "prompts"
    
    # Simulate loading system prompt
    system_prompt = prompts_dir / "system_prompt.txt"
    logger.info(f"Loading system prompt from: {system_prompt}")
    with open(system_prompt, 'r') as f:
        prompt_text = f.read()
        logger.info(f"System prompt: {prompt_text[:50]}...")
    
    # Simulate loading user prompt template
    user_prompt = prompts_dir / "classification_prompt.txt"
    logger.info(f"Loading user prompt from: {user_prompt}")
    with open(user_prompt, 'r') as f:
        template = f.read()
        logger.info(f"User prompt template: {template[:50]}...")
    
    time.sleep(0.5)  # Simulate processing time

def simulate_inference():
    """Simulate running inference."""
    logger.info("🔮 Running inference...")
    
    # Simulate some computation
    for i in range(3):
        logger.info(f"Processing batch {i+1}/3...")
        time.sleep(1)
    
    logger.info("Inference completed!")

def simulate_huggingface_download():
    """Simulate downloading from HuggingFace (creates cache-like paths)."""
    logger.info("🤗 Simulating HuggingFace model download...")
    
    # Create HF cache-like directory structure
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Simulate model cache
    model_cache = cache_dir / "models--bert-base-uncased"
    model_cache.mkdir(exist_ok=True)
    
    # Create fake cached files
    cached_model = model_cache / "pytorch_model.bin"
    with open(cached_model, 'wb') as f:
        f.write(b"CACHED_MODEL_DATA" * 500)
    
    cached_config = model_cache / "config.json"
    with open(cached_config, 'w') as f:
        json.dump({"model_type": "bert", "hidden_size": 768}, f)
    
    logger.info(f"Simulated HF cache at: {model_cache}")
    
    # Simulate reading from cache
    with open(cached_model, 'rb') as f:
        data = f.read()
        logger.info(f"Read cached model: {len(data)} bytes")
    
    time.sleep(1)

def main():
    """Main demonstration function."""
    logger.info("🚀 Starting ML application demonstration")
    logger.info("This application will create and access AI/ML artifacts that should be captured by runtime tracing")
    
    try:
        # Create sample artifacts
        artifacts_dir = create_sample_artifacts()
        
        # Simulate typical ML workflow
        simulate_huggingface_download()
        simulate_model_loading(artifacts_dir)
        simulate_dataset_loading(artifacts_dir)
        simulate_prompt_loading(artifacts_dir)
        simulate_inference()
        
        logger.info("✅ ML application demonstration completed successfully!")
        logger.info("Check the runtime tracing results in the UI")
        
        # Keep the process running for a bit to ensure tracing captures everything
        logger.info("Keeping process alive for 5 more seconds...")
        time.sleep(5)
        
    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        raise
    
    finally:
        # Cleanup
        import shutil
        if 'artifacts_dir' in locals():
            shutil.rmtree(artifacts_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary artifacts: {artifacts_dir}")

if __name__ == "__main__":
    main()