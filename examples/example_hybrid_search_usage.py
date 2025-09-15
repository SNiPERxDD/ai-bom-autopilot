#!/usr/bin/env python3
"""
Example usage of HybridSearchEngine

This script demonstrates how to use the HybridSearchEngine for:
- Performing hybrid search combining vector and keyword search
- Getting search capabilities and status
- Handling different search scenarios

Requirements: 6.2, 6.4, 6.5
"""

import sys
import os
import json
from typing import List

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.search.engine import HybridSearchEngine, SearchResult

def demonstrate_search_capabilities():
    """Demonstrate search capabilities reporting"""
    print("🔍 HybridSearchEngine Capabilities")
    print("=" * 50)
    
    # Initialize search engine
    search_engine = HybridSearchEngine()
    
    # Get capabilities
    capabilities = search_engine.get_search_capabilities()
    
    print("Vector Search:")
    vector_caps = capabilities['vector_search']
    print(f"  Available: {vector_caps['available']}")
    print(f"  Provider: {vector_caps['embedding_provider']}")
    print(f"  Client Ready: {vector_caps['embedding_client']}")
    print(f"  Dimensions: {vector_caps['dimensions']}")
    
    print("\nFulltext Search:")
    fulltext_caps = capabilities['fulltext_search']
    print(f"  Available: {fulltext_caps['available']}")
    print(f"  BM25 Fallback: {fulltext_caps['fallback_to_bm25']}")
    
    print("\nHybrid Fusion:")
    fusion_caps = capabilities['hybrid_fusion']
    print(f"  Method: {fusion_caps['method']}")
    print(f"  RRF K-value: {fusion_caps['rrf_k']}")
    
    print("\nFallback Search:")
    fallback_caps = capabilities['fallback_search']
    print(f"  Method: {fallback_caps['method']}")
    print(f"  Available: {fallback_caps['available']}")
    
    return search_engine

def demonstrate_search_usage(search_engine: HybridSearchEngine):
    """Demonstrate search usage with mock data"""
    print("\n🔍 Search Usage Examples")
    print("=" * 50)
    
    # Example search queries
    queries = [
        "machine learning model",
        "data preprocessing",
        "tensorflow training",
        "model evaluation metrics"
    ]
    
    project_id = 1  # Example project ID
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        print("-" * 30)
        
        try:
            # Perform hybrid search
            results = search_engine.search(
                project_id=project_id,
                query_text=query,
                top_k=5
            )
            
            if results:
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. {result.ref_path} (chunk {result.chunk_ix})")
                    print(f"     Score: {result.score:.4f} | Type: {result.search_type}")
                    print(f"     Text: {result.text[:80]}...")
            else:
                print("  No results found (expected with empty database)")
                
        except Exception as e:
            print(f"  Search failed: {e}")

def demonstrate_individual_search_methods(search_engine: HybridSearchEngine):
    """Demonstrate individual search methods"""
    print("\n🔍 Individual Search Methods")
    print("=" * 50)
    
    project_id = 1
    query = "machine learning"
    limit = 5
    
    print(f"Query: '{query}' | Project: {project_id} | Limit: {limit}")
    print()
    
    # Test vector search
    print("1. Vector Search (VEC_COSINE_DISTANCE):")
    try:
        vector_results = search_engine._vector_search(project_id, query, limit)
        if vector_results:
            print(f"   Found {len(vector_results)} vector results")
            for result in vector_results[:2]:  # Show first 2
                print(f"   - {result.ref_path}: {result.score:.4f}")
        else:
            print("   No vector results (expected without embeddings/data)")
    except Exception as e:
        print(f"   Vector search error: {e}")
    
    # Test keyword search
    print("\n2. Keyword Search (FULLTEXT/BM25):")
    try:
        keyword_results = search_engine._keyword_search(project_id, query, limit)
        if keyword_results:
            print(f"   Found {len(keyword_results)} keyword results")
            for result in keyword_results[:2]:  # Show first 2
                print(f"   - {result.ref_path}: {result.score:.4f}")
        else:
            print("   No keyword results (expected without data)")
    except Exception as e:
        print(f"   Keyword search error: {e}")
    
    # Test fallback search
    print("\n3. Fallback Search (LIKE):")
    try:
        fallback_results = search_engine._fallback_search(project_id, query, limit)
        if fallback_results:
            print(f"   Found {len(fallback_results)} fallback results")
            for result in fallback_results[:2]:  # Show first 2
                print(f"   - {result.ref_path}: {result.score:.4f}")
        else:
            print("   No fallback results (expected without data)")
    except Exception as e:
        print(f"   Fallback search error: {e}")

def demonstrate_search_result_format():
    """Demonstrate SearchResult data structure"""
    print("\n📋 SearchResult Data Structure")
    print("=" * 50)
    
    # Create example search result
    example_result = SearchResult(
        id=123,
        ref_path="src/models/transformer.py",
        chunk_ix=2,
        text="This chunk contains information about transformer model architecture and training procedures.",
        ref_type="file",
        commit_sha="abc123def456",
        token_count=15,
        meta={"file_size": 2048, "language": "python"},
        score=0.8542,
        search_type="hybrid"
    )
    
    print("Example SearchResult:")
    print(json.dumps(example_result.to_dict(), indent=2))
    
    print("\nKey Fields:")
    print("- id: Unique chunk identifier")
    print("- ref_path: File path relative to repository root")
    print("- chunk_ix: Chunk index within the file")
    print("- text: The actual text content")
    print("- score: Relevance score (higher = more relevant)")
    print("- search_type: 'vector', 'keyword', 'hybrid', or 'fallback'")

def main():
    """Main demonstration function"""
    print("🚀 HybridSearchEngine Usage Examples")
    print("=" * 60)
    print()
    print("This script demonstrates the HybridSearchEngine implementation")
    print("that combines vector similarity and keyword search with RRF fusion.")
    print()
    print("Features implemented:")
    print("✅ VEC_COSINE_DISTANCE queries for vector search")
    print("✅ MATCH(...) AGAINST(...) for FULLTEXT search")
    print("✅ BM25 fallback when FTS unavailable")
    print("✅ RRF fusion logic for combining results")
    print("✅ Comprehensive error handling and graceful degradation")
    print()
    
    try:
        # Initialize and demonstrate capabilities
        search_engine = demonstrate_search_capabilities()
        
        # Demonstrate search usage
        demonstrate_search_usage(search_engine)
        
        # Demonstrate individual methods
        demonstrate_individual_search_methods(search_engine)
        
        # Demonstrate result format
        demonstrate_search_result_format()
        
        print("\n🎉 HybridSearchEngine demonstration completed!")
        print("\nNext steps:")
        print("1. Configure TiDB connection for live database testing")
        print("2. Populate evidence_chunks table with actual data")
        print("3. Configure embedding provider (OpenAI/Gemini) for vector search")
        print("4. Test with real queries and data")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()