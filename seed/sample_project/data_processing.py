#!/usr/bin/env python3
"""
Data processing pipeline for ML training
"""

from datasets import load_dataset, Dataset
from transformers import AutoTokenizer
import pandas as pd
from typing import Dict, List, Any
import json

# Dataset configurations
DATASETS_CONFIG = {
    "imdb": {
        "name": "imdb",
        "split": "train",
        "text_column": "text",
        "label_column": "label"
    },
    "squad": {
        "name": "squad",
        "split": "train",
        "context_column": "context",
        "question_column": "question",
        "answer_column": "answers"
    }
}

class DataProcessor:
    """Handles data loading and preprocessing"""
    
    def __init__(self, tokenizer_name: str = "bert-base-uncased"):
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        
    def load_imdb_dataset(self) -> Dataset:
        """Load and preprocess IMDB dataset"""
        dataset = load_dataset("imdb")
        return dataset["train"]
    
    def load_squad_dataset(self) -> Dataset:
        """Load and preprocess SQuAD dataset"""
        dataset = load_dataset("squad")
        return dataset["train"]
    
    def preprocess_classification_data(self, dataset: Dataset) -> Dataset:
        """Preprocess data for text classification"""
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding="max_length",
                max_length=512
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        return tokenized_dataset
    
    def preprocess_qa_data(self, dataset: Dataset) -> Dataset:
        """Preprocess data for question answering"""
        def prepare_qa_features(examples):
            questions = [q.strip() for q in examples["question"]]
            contexts = examples["context"]
            
            inputs = self.tokenizer(
                questions,
                contexts,
                truncation=True,
                padding="max_length",
                max_length=512,
                return_offsets_mapping=True
            )
            
            return inputs
        
        processed_dataset = dataset.map(prepare_qa_features, batched=True)
        return processed_dataset

def create_synthetic_data() -> Dict[str, Any]:
    """Create synthetic training data for testing"""
    synthetic_reviews = [
        {"text": "This movie was absolutely fantastic! Great acting and plot.", "label": 1},
        {"text": "Terrible movie, waste of time. Poor acting and boring story.", "label": 0},
        {"text": "Average movie, nothing special but not bad either.", "label": 1},
        {"text": "Outstanding cinematography and brilliant performances.", "label": 1},
        {"text": "Disappointing sequel, doesn't live up to the original.", "label": 0}
    ]
    
    synthetic_qa = [
        {
            "context": "The Transformer architecture was introduced in 2017 by Vaswani et al.",
            "question": "When was the Transformer architecture introduced?",
            "answer": "2017"
        },
        {
            "context": "BERT uses bidirectional training of Transformer encoders.",
            "question": "What type of training does BERT use?",
            "answer": "bidirectional training"
        }
    ]
    
    return {
        "classification": synthetic_reviews,
        "qa": synthetic_qa
    }

if __name__ == "__main__":
    # Example usage
    processor = DataProcessor()
    
    print("Loading IMDB dataset...")
    imdb_data = processor.load_imdb_dataset()
    print(f"IMDB dataset size: {len(imdb_data)}")
    
    print("Creating synthetic data...")
    synthetic_data = create_synthetic_data()
    print(f"Synthetic classification samples: {len(synthetic_data['classification'])}")
    print(f"Synthetic QA samples: {len(synthetic_data['qa'])}")