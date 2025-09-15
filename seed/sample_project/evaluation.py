#!/usr/bin/env python3
"""
Model evaluation and benchmarking script
"""

import torch
from transformers import AutoModel, AutoTokenizer, pipeline
from datasets import load_dataset
from sklearn.metrics import accuracy_score, classification_report
import json
import time
from typing import Dict, List, Any
import numpy as np

# Model configurations for evaluation
EVAL_MODELS = {
    "bert-base": "bert-base-uncased",
    "distilbert": "distilbert-base-uncased", 
    "roberta": "roberta-base"
}

class ModelEvaluator:
    """Comprehensive model evaluation suite"""
    
    def __init__(self):
        self.results = {}
        
    def evaluate_classification_models(self) -> Dict[str, Any]:
        """Evaluate multiple classification models"""
        print("Evaluating classification models...")
        
        # Load test dataset
        dataset = load_dataset("imdb", split="test[:100]")  # Small subset for demo
        texts = dataset["text"]
        labels = dataset["label"]
        
        results = {}
        
        for model_name, model_path in EVAL_MODELS.items():
            print(f"Evaluating {model_name}...")
            
            try:
                # Create classification pipeline
                classifier = pipeline(
                    "sentiment-analysis",
                    model=model_path,
                    tokenizer=model_path,
                    return_all_scores=True
                )
                
                # Measure inference time
                start_time = time.time()
                predictions = []
                
                for text in texts:
                    result = classifier(text[:512])  # Truncate for speed
                    # Convert to binary prediction (0=negative, 1=positive)
                    pred = 1 if result[0]["label"] == "POSITIVE" else 0
                    predictions.append(pred)
                
                end_time = time.time()
                
                # Calculate metrics
                accuracy = accuracy_score(labels, predictions)
                inference_time = end_time - start_time
                
                results[model_name] = {
                    "accuracy": accuracy,
                    "inference_time": inference_time,
                    "samples_per_second": len(texts) / inference_time,
                    "model_path": model_path
                }
                
                print(f"{model_name} - Accuracy: {accuracy:.3f}, Time: {inference_time:.2f}s")
                
            except Exception as e:
                print(f"Error evaluating {model_name}: {e}")
                results[model_name] = {"error": str(e)}
        
        return results
    
    def benchmark_embedding_models(self) -> Dict[str, Any]:
        """Benchmark embedding model performance"""
        print("Benchmarking embedding models...")
        
        from sentence_transformers import SentenceTransformer
        
        # Test sentences
        sentences = [
            "This is a sample sentence for embedding.",
            "Machine learning models process natural language.",
            "Transformers have revolutionized NLP tasks.",
            "Deep learning requires large amounts of data.",
            "Artificial intelligence is transforming industries."
        ]
        
        embedding_models = {
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2"
        }
        
        results = {}
        
        for model_name, model_path in embedding_models.items():
            try:
                print(f"Testing {model_name}...")
                
                model = SentenceTransformer(model_path)
                
                # Measure embedding time
                start_time = time.time()
                embeddings = model.encode(sentences)
                end_time = time.time()
                
                results[model_name] = {
                    "embedding_dim": embeddings.shape[1],
                    "encoding_time": end_time - start_time,
                    "sentences_per_second": len(sentences) / (end_time - start_time),
                    "model_path": model_path
                }
                
                print(f"{model_name} - Dim: {embeddings.shape[1]}, Time: {end_time - start_time:.3f}s")
                
            except Exception as e:
                print(f"Error with {model_name}: {e}")
                results[model_name] = {"error": str(e)}
        
        return results
    
    def test_openai_integration(self) -> Dict[str, Any]:
        """Test OpenAI API integration"""
        print("Testing OpenAI integration...")
        
        try:
            import openai
            client = openai.OpenAI()
            
            # Test prompt
            test_prompt = "Classify the sentiment of this text: 'I love this movie!'"
            
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": test_prompt}],
                max_tokens=50
            )
            end_time = time.time()
            
            return {
                "status": "success",
                "response_time": end_time - start_time,
                "model": "gpt-3.5-turbo",
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run all evaluation benchmarks"""
        print("Starting comprehensive model evaluation...")
        
        results = {
            "classification_models": self.evaluate_classification_models(),
            "embedding_models": self.benchmark_embedding_models(),
            "openai_integration": self.test_openai_integration(),
            "evaluation_timestamp": time.time()
        }
        
        # Save results
        with open("evaluation_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print("Evaluation completed! Results saved to evaluation_results.json")
        return results

def main():
    """Main evaluation function"""
    evaluator = ModelEvaluator()
    results = evaluator.run_comprehensive_evaluation()
    
    # Print summary
    print("\n=== Evaluation Summary ===")
    
    if "classification_models" in results:
        print("\nClassification Models:")
        for model, metrics in results["classification_models"].items():
            if "accuracy" in metrics:
                print(f"  {model}: {metrics['accuracy']:.3f} accuracy")
    
    if "embedding_models" in results:
        print("\nEmbedding Models:")
        for model, metrics in results["embedding_models"].items():
            if "embedding_dim" in metrics:
                print(f"  {model}: {metrics['embedding_dim']}D embeddings")
    
    if "openai_integration" in results:
        status = results["openai_integration"]["status"]
        print(f"\nOpenAI Integration: {status}")

if __name__ == "__main__":
    main()