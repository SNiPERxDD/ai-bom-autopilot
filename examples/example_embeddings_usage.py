#!/usr/bin/env python3
"""
Example usage of the EmbeddingService
"""

import os
import sys
from unittest.mock import patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.embeddings.embedder import EmbeddingService
from core.schemas.models import EvidenceChunk, RefType, ScanState, Project

def example_usage():
    """Example of how to use the EmbeddingService"""
    
    print("=== EmbeddingService Usage Example ===\n")
    
    # Mock the database manager for this example
    with patch('core.embeddings.embedder.db_manager') as mock_db:
        mock_db.capabilities = {'vector': True, 'fulltext': False}
        
        # Initialize the service
        print("1. Initializing EmbeddingService...")
        service = EmbeddingService()
        print(f"   Provider: {service.provider}")
        print(f"   Dimensions: {service.dimensions}")
        print(f"   Model: {service.model}")
        print()
        
        # Example 1: Text chunking
        print("2. Text Chunking Example...")
        sample_text = """
        This is a sample document that demonstrates how the embedding service
        works with text chunking. The service will split long documents into
        smaller chunks that can be processed by embedding models. Each chunk
        will have overlapping content to maintain context between chunks.
        
        The chunking process considers token limits and ensures that no important
        information is lost during the splitting process. This is crucial for
        maintaining the semantic meaning of the original document.
        """
        
        chunks = service._split_text(sample_text)
        print(f"   Original text length: {len(sample_text)} characters")
        print(f"   Number of chunks created: {len(chunks)}")
        print(f"   First chunk preview: {chunks[0][:100]}...")
        print()
        
        # Example 2: Reference type detection
        print("3. Reference Type Detection Example...")
        test_files = [
            "README.md",
            "config.yaml", 
            "settings.json",
            "main.py",
            "model.pkl"
        ]
        
        for file_path in test_files:
            ref_type = service._determine_ref_type(file_path)
            print(f"   {file_path} -> {ref_type.value}")
        print()
        
        # Example 3: Creating evidence chunks
        print("4. Evidence Chunk Creation Example...")
        project_id = 1
        
        evidence_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk = EvidenceChunk(
                project_id=project_id,
                ref_type=RefType.FILE,
                ref_path="example.md",
                commit_sha="abc123def",
                chunk_ix=i,
                text=chunk_text,
                token_count=len(service.encoding.encode(chunk_text)),
                meta={"source": "example", "processed": True}
            )
            evidence_chunks.append(chunk)
        
        print(f"   Created {len(evidence_chunks)} evidence chunks")
        for i, chunk in enumerate(evidence_chunks):
            print(f"   Chunk {i}: {chunk.token_count} tokens, ref_type={chunk.ref_type.value}")
        print()
        
        # Example 4: RRF Fusion demonstration
        print("5. Reciprocal Rank Fusion Example...")
        
        # Mock search results
        vector_results = [
            ({'id': 1, 'text': 'machine learning model', 'ref_path': 'ml.py'}, 0.1),
            ({'id': 2, 'text': 'data processing pipeline', 'ref_path': 'data.py'}, 0.2),
            ({'id': 3, 'text': 'neural network architecture', 'ref_path': 'nn.py'}, 0.3),
        ]
        
        keyword_results = [
            ({'id': 3, 'text': 'neural network architecture', 'ref_path': 'nn.py'}, 0.9),
            ({'id': 1, 'text': 'machine learning model', 'ref_path': 'ml.py'}, 0.8),
            ({'id': 4, 'text': 'training configuration', 'ref_path': 'config.py'}, 0.7),
        ]
        
        fused_results = service._reciprocal_rank_fusion(vector_results, keyword_results, limit=5)
        
        print("   Vector search results:")
        for result, score in vector_results:
            print(f"     {result['id']}: {result['text']} (distance: {score})")
        
        print("   Keyword search results:")
        for result, score in keyword_results:
            print(f"     {result['id']}: {result['text']} (score: {score})")
        
        print("   Fused results (RRF):")
        for result in fused_results:
            print(f"     {result['id']}: {result['text']} (RRF score: {result['rrf_score']:.4f})")
        print()
        
        print("=== Example Complete ===")

if __name__ == "__main__":
    example_usage()