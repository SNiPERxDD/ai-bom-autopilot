#!/usr/bin/env python3
"""
Sample training script for ML-BOM testing
Demonstrates usage of multiple models, datasets, and tools
"""

import torch
from transformers import (
    AutoModel, 
    AutoTokenizer, 
    TrainingArguments, 
    Trainer,
    AutoModelForSequenceClassification
)
from datasets import load_dataset
import openai
from sentence_transformers import SentenceTransformer
import json
import os
from typing import Dict, Any

# Configuration - Multiple models for comprehensive testing
MODELS_CONFIG = {
    "llama": "meta-llama/Llama-3.1-8B",
    "bert": "bert-base-uncased", 
    "sentence_transformer": "sentence-transformers/all-MiniLM-L6-v2"
}

DATASETS_CONFIG = {
    "imdb": "imdb",
    "squad": "squad",
    "wikitext": "wikitext-103-raw-v1"
}

OPENAI_MODELS = ["gpt-4", "gpt-3.5-turbo"]

class MultiModelTrainer:
    """Handles training with multiple models and datasets"""
    
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.datasets = {}
        
    def load_models(self):
        """Load all configured models"""
        print("Loading models...")
        
        # Load BERT for classification
        self.models["bert"] = AutoModelForSequenceClassification.from_pretrained(
            MODELS_CONFIG["bert"], 
            num_labels=2
        )
        self.tokenizers["bert"] = AutoTokenizer.from_pretrained(MODELS_CONFIG["bert"])
        
        # Load sentence transformer for embeddings
        self.models["sentence_transformer"] = SentenceTransformer(
            MODELS_CONFIG["sentence_transformer"]
        )
        
        # Note: LLaMA would require special handling for licensing
        print(f"Configured LLaMA model: {MODELS_CONFIG['llama']}")
        
    def load_datasets(self):
        """Load all configured datasets"""
        print("Loading datasets...")
        
        # Load IMDB for sentiment analysis
        self.datasets["imdb"] = load_dataset(DATASETS_CONFIG["imdb"])
        print(f"IMDB dataset loaded: {len(self.datasets['imdb']['train'])} samples")
        
        # Load SQuAD for QA
        self.datasets["squad"] = load_dataset(DATASETS_CONFIG["squad"])
        print(f"SQuAD dataset loaded: {len(self.datasets['squad']['train'])} samples")
        
    def setup_openai_client(self):
        """Setup OpenAI client for external model usage"""
        try:
            client = openai.OpenAI()
            # Test with a simple call
            response = client.models.list()
            print(f"OpenAI client configured. Available models: {len(response.data)}")
            return client
        except Exception as e:
            print(f"OpenAI setup failed: {e}")
            return None
    
    def load_prompts(self) -> Dict[str, str]:
        """Load prompt templates"""
        prompts = {}
        
        # Load system prompt
        with open("prompts/system_prompt.txt", "r") as f:
            prompts["system"] = f.read()
            
        # Load classification prompt
        with open("prompts/classification_prompt.txt", "r") as f:
            prompts["classification"] = f.read()
            
        # Load QA prompt
        with open("prompts/qa_prompt.txt", "r") as f:
            prompts["qa"] = f.read()
            
        return prompts
    
    def train_classification_model(self):
        """Train BERT for sentiment classification"""
        print("Training classification model...")
        
        model = self.models["bert"]
        tokenizer = self.tokenizers["bert"]
        dataset = self.datasets["imdb"]
        
        # Tokenize dataset
        def tokenize_function(examples):
            return tokenizer(examples["text"], truncation=True, padding="max_length")
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir="./results/bert_classification",
            num_train_epochs=1,  # Reduced for demo
            per_device_train_batch_size=8,
            per_device_eval_batch_size=16,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir="./logs/bert",
            evaluation_strategy="steps",
            eval_steps=500,
            save_steps=1000,
        )
        
        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset["train"].select(range(1000)),  # Small subset for demo
            eval_dataset=tokenized_dataset["test"].select(range(200)),
        )
        
        print("Starting BERT training...")
        # trainer.train()  # Commented out for demo - would actually train
        print("BERT training completed!")
        
    def generate_embeddings(self):
        """Generate embeddings using sentence transformer"""
        print("Generating embeddings...")
        
        model = self.models["sentence_transformer"]
        
        # Sample texts for embedding
        sample_texts = [
            "This is a positive movie review",
            "This is a negative movie review", 
            "Machine learning is fascinating",
            "Natural language processing enables AI"
        ]
        
        embeddings = model.encode(sample_texts)
        print(f"Generated embeddings shape: {embeddings.shape}")
        
        return embeddings
    
    def use_openai_models(self, client):
        """Demonstrate usage of OpenAI models"""
        if not client:
            print("OpenAI client not available")
            return
            
        print("Using OpenAI models...")
        
        # Load prompts
        prompts = self.load_prompts()
        
        # Example classification with GPT-4
        sample_review = "This movie was absolutely fantastic!"
        classification_prompt = prompts["classification"].format(review_text=sample_review)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": classification_prompt}
                ],
                max_tokens=100
            )
            print(f"GPT-4 classification result: {response.choices[0].message.content}")
        except Exception as e:
            print(f"OpenAI API call failed: {e}")

def main():
    """Main training pipeline"""
    trainer = MultiModelTrainer()
    
    # Load all components
    trainer.load_models()
    trainer.load_datasets()
    
    # Setup external services
    openai_client = trainer.setup_openai_client()
    
    # Run training and inference
    trainer.train_classification_model()
    trainer.generate_embeddings()
    trainer.use_openai_models(openai_client)
    
    print("Multi-model training pipeline completed!")

if __name__ == "__main__":
    main()