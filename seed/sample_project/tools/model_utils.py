#!/usr/bin/env python3
"""
Utility functions for model management and evaluation
"""

import torch
from transformers import AutoModel, AutoTokenizer
from typing import Dict, List, Any
import json

class ModelManager:
    """Manages loading and configuration of ML models"""
    
    def __init__(self, config_path: str = "models/model_config.json"):
        self.config_path = config_path
        self.models = {}
        self.tokenizers = {}
        
    def load_config(self) -> Dict[str, Any]:
        """Load model configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def load_model(self, model_name: str) -> torch.nn.Module:
        """Load a model by name"""
        if model_name not in self.models:
            if "openai" in model_name:
                # Handle OpenAI models differently
                self.models[model_name] = f"openai_client:{model_name}"
            else:
                # Load HuggingFace models
                self.models[model_name] = AutoModel.from_pretrained(model_name)
                self.tokenizers[model_name] = AutoTokenizer.from_pretrained(model_name)
        
        return self.models[model_name]
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get model metadata"""
        config = self.load_config()
        for model in config["models"]:
            if model["name"] == model_name:
                return model
        return {}

class EvaluationTools:
    """Tools for model evaluation and benchmarking"""
    
    @staticmethod
    def calculate_metrics(predictions: List[str], targets: List[str]) -> Dict[str, float]:
        """Calculate evaluation metrics"""
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
        
        accuracy = accuracy_score(targets, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            targets, predictions, average='weighted'
        )
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
    
    @staticmethod
    def benchmark_inference_speed(model, tokenizer, texts: List[str]) -> Dict[str, float]:
        """Benchmark model inference speed"""
        import time
        
        start_time = time.time()
        
        for text in texts:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = model(**inputs)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_sample = total_time / len(texts)
        
        return {
            "total_time": total_time,
            "avg_time_per_sample": avg_time_per_sample,
            "samples_per_second": len(texts) / total_time
        }