#!/usr/bin/env python3
"""
Database initialization script for demo project
Creates initial project data for ML-BOM Autopilot demonstration
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add the parent directory to sys.path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db.connection import get_db_connection
from core.schemas.models import Project, Model, Dataset, Prompt, Tool

class DemoProjectInitializer:
    """Initializes demo project data in the database"""
    
    def __init__(self):
        self.db = get_db_connection()
        self.project_id = None
        
    def create_demo_project(self) -> int:
        """Create the main demo project"""
        print("Creating demo project...")
        
        project_data = {
            "name": "sample-ml-project",
            "description": "Sample ML project for AI-BOM Autopilot testing",
            "repo_url": "file://./seed/sample_project",
            "branch": "main",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        cursor = self.db.cursor()
        
        # Insert project
        insert_query = """
        INSERT INTO projects (name, description, repo_url, branch, created_at, updated_at)
        VALUES (%(name)s, %(description)s, %(repo_url)s, %(branch)s, %(created_at)s, %(updated_at)s)
        """
        
        cursor.execute(insert_query, project_data)
        project_id = cursor.lastrowid
        self.project_id = project_id
        
        print(f"Created project with ID: {project_id}")
        return project_id
    
    def create_demo_models(self):
        """Create demo model entries"""
        print("Creating demo models...")
        
        models_data = [
            {
                "project_id": self.project_id,
                "name": "meta-llama/Llama-3.1-8B",
                "version": "1.0.0",
                "provider": "huggingface",
                "license_spdx": "custom",
                "file_path": "models/model_config.json",
                "content_hash": self._calculate_hash("meta-llama/Llama-3.1-8B:1.0.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "causal-lm",
                    "parameters": "8B",
                    "use_case": "text_generation",
                    "architecture": "transformer"
                })
            },
            {
                "project_id": self.project_id,
                "name": "bert-base-uncased",
                "version": "1.0.0",
                "provider": "huggingface",
                "license_spdx": "Apache-2.0",
                "file_path": "train.py",
                "content_hash": self._calculate_hash("bert-base-uncased:1.0.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "masked-lm",
                    "parameters": "110M",
                    "use_case": "text_classification",
                    "architecture": "transformer"
                })
            },
            {
                "project_id": self.project_id,
                "name": "sentence-transformers/all-MiniLM-L6-v2",
                "version": "1.0.0",
                "provider": "huggingface",
                "license_spdx": "Apache-2.0",
                "file_path": "train.py",
                "content_hash": self._calculate_hash("sentence-transformers/all-MiniLM-L6-v2:1.0.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "sentence-transformer",
                    "parameters": "22M",
                    "use_case": "embeddings",
                    "architecture": "transformer"
                })
            },
            {
                "project_id": self.project_id,
                "name": "openai/gpt-4",
                "version": "gpt-4-0613",
                "provider": "openai",
                "license_spdx": "proprietary",
                "file_path": "train.py",
                "content_hash": self._calculate_hash("openai/gpt-4:gpt-4-0613"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "causal-lm",
                    "parameters": "unknown",
                    "use_case": "reasoning",
                    "architecture": "transformer"
                })
            }
        ]
        
        cursor = self.db.cursor()
        
        insert_query = """
        INSERT INTO models (project_id, name, version, provider, license_spdx, 
                           file_path, content_hash, commit_sha, metadata, created_at)
        VALUES (%(project_id)s, %(name)s, %(version)s, %(provider)s, %(license_spdx)s,
                %(file_path)s, %(content_hash)s, %(commit_sha)s, %(metadata)s, NOW())
        """
        
        for model_data in models_data:
            cursor.execute(insert_query, model_data)
            print(f"Created model: {model_data['name']}")
    
    def create_demo_datasets(self):
        """Create demo dataset entries"""
        print("Creating demo datasets...")
        
        datasets_data = [
            {
                "project_id": self.project_id,
                "name": "imdb",
                "version": "1.0.0",
                "provider": "huggingface",
                "license_spdx": "Apache-2.0",
                "file_path": "datasets/dataset_manifest.yaml",
                "content_hash": self._calculate_hash("imdb:1.0.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "text_classification",
                    "size": "25000 samples",
                    "description": "Movie reviews for sentiment analysis"
                })
            },
            {
                "project_id": self.project_id,
                "name": "squad",
                "version": "1.1.0",
                "provider": "huggingface",
                "license_spdx": "CC BY-SA 4.0",
                "file_path": "data_processing.py",
                "content_hash": self._calculate_hash("squad:1.1.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "question_answering",
                    "size": "100k+ samples",
                    "description": "Reading comprehension dataset"
                })
            },
            {
                "project_id": self.project_id,
                "name": "wikitext-103",
                "version": "1.0.0",
                "provider": "huggingface",
                "license_spdx": "CC BY-SA 3.0",
                "file_path": "train.py",
                "content_hash": self._calculate_hash("wikitext-103:1.0.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "language_modeling",
                    "size": "103M tokens",
                    "description": "Wikipedia articles for language modeling"
                })
            }
        ]
        
        cursor = self.db.cursor()
        
        insert_query = """
        INSERT INTO datasets (project_id, name, version, provider, license_spdx,
                             file_path, content_hash, commit_sha, metadata, created_at)
        VALUES (%(project_id)s, %(name)s, %(version)s, %(provider)s, %(license_spdx)s,
                %(file_path)s, %(content_hash)s, %(commit_sha)s, %(metadata)s, NOW())
        """
        
        for dataset_data in datasets_data:
            cursor.execute(insert_query, dataset_data)
            print(f"Created dataset: {dataset_data['name']}")
    
    def create_demo_prompts(self):
        """Create demo prompt entries"""
        print("Creating demo prompts...")
        
        # First, create prompt blobs for deduplication
        prompt_contents = {
            "system_prompt": "You are a helpful AI assistant specialized in machine learning...",
            "classification_prompt": "You are an expert text classifier. Your task is to classify...",
            "qa_prompt": "You are a helpful assistant that answers questions based on..."
        }
        
        cursor = self.db.cursor()
        
        # Insert prompt blobs
        for prompt_name, content in prompt_contents.items():
            content_hash = self._calculate_hash(content)
            
            blob_query = """
            INSERT IGNORE INTO prompt_blobs (content_hash, content, created_at)
            VALUES (%s, %s, NOW())
            """
            cursor.execute(blob_query, (content_hash, content))
        
        # Create prompt entries
        prompts_data = [
            {
                "project_id": self.project_id,
                "name": "system_prompt",
                "version": "1.0.0",
                "file_path": "prompts/system_prompt.txt",
                "content_hash": self._calculate_hash(prompt_contents["system_prompt"]),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "system",
                    "purpose": "AI assistant configuration",
                    "protected": True
                })
            },
            {
                "project_id": self.project_id,
                "name": "classification_prompt",
                "version": "1.0.0",
                "file_path": "prompts/classification_prompt.txt",
                "content_hash": self._calculate_hash(prompt_contents["classification_prompt"]),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "task",
                    "purpose": "sentiment classification",
                    "protected": False
                })
            },
            {
                "project_id": self.project_id,
                "name": "qa_prompt",
                "version": "1.0.0",
                "file_path": "prompts/qa_prompt.txt",
                "content_hash": self._calculate_hash(prompt_contents["qa_prompt"]),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "task",
                    "purpose": "question answering",
                    "protected": True
                })
            }
        ]
        
        insert_query = """
        INSERT INTO prompts (project_id, name, version, file_path, content_hash,
                            commit_sha, metadata, created_at)
        VALUES (%(project_id)s, %(name)s, %(version)s, %(file_path)s, %(content_hash)s,
                %(commit_sha)s, %(metadata)s, NOW())
        """
        
        for prompt_data in prompts_data:
            cursor.execute(insert_query, prompt_data)
            print(f"Created prompt: {prompt_data['name']}")
    
    def create_demo_tools(self):
        """Create demo tool entries"""
        print("Creating demo tools...")
        
        tools_data = [
            {
                "project_id": self.project_id,
                "name": "transformers",
                "version": "4.35.0",
                "provider": "huggingface",
                "license_spdx": "Apache-2.0",
                "file_path": "requirements.txt",
                "content_hash": self._calculate_hash("transformers:4.35.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "library",
                    "category": "ml_framework",
                    "language": "python"
                })
            },
            {
                "project_id": self.project_id,
                "name": "torch",
                "version": "2.1.0",
                "provider": "pytorch",
                "license_spdx": "BSD-3-Clause",
                "file_path": "requirements.txt",
                "content_hash": self._calculate_hash("torch:2.1.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "library",
                    "category": "deep_learning",
                    "language": "python"
                })
            },
            {
                "project_id": self.project_id,
                "name": "openai",
                "version": "1.3.0",
                "provider": "openai",
                "license_spdx": "MIT",
                "file_path": "requirements.txt",
                "content_hash": self._calculate_hash("openai:1.3.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "api_client",
                    "category": "external_service",
                    "language": "python"
                })
            },
            {
                "project_id": self.project_id,
                "name": "scikit-learn",
                "version": "1.3.0",
                "provider": "scikit-learn",
                "license_spdx": "BSD-3-Clause",
                "file_path": "requirements.txt",
                "content_hash": self._calculate_hash("scikit-learn:1.3.0"),
                "commit_sha": "abc123def456",
                "metadata": json.dumps({
                    "type": "library",
                    "category": "ml_framework",
                    "language": "python"
                })
            }
        ]
        
        cursor = self.db.cursor()
        
        insert_query = """
        INSERT INTO tools (project_id, name, version, provider, license_spdx,
                          file_path, content_hash, commit_sha, metadata, created_at)
        VALUES (%(project_id)s, %(name)s, %(version)s, %(provider)s, %(license_spdx)s,
                %(file_path)s, %(content_hash)s, %(commit_sha)s, %(metadata)s, NOW())
        """
        
        for tool_data in tools_data:
            cursor.execute(insert_query, tool_data)
            print(f"Created tool: {tool_data['name']}")
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def initialize_demo_data(self):
        """Initialize all demo data"""
        print("Initializing demo project data...")
        
        try:
            # Create project
            project_id = self.create_demo_project()
            
            # Create all artifacts
            self.create_demo_models()
            self.create_demo_datasets()
            self.create_demo_prompts()
            self.create_demo_tools()
            
            # Commit transaction
            self.db.commit()
            
            print(f"✅ Demo project initialized successfully with ID: {project_id}")
            print(f"Project name: sample-ml-project")
            print(f"Repository: file://./seed/sample_project")
            
            return project_id
            
        except Exception as e:
            print(f"❌ Error initializing demo data: {e}")
            self.db.rollback()
            raise
        finally:
            self.db.close()

def main():
    """Main function to initialize demo project"""
    print("=== ML-BOM Autopilot Demo Project Initializer ===")
    
    try:
        initializer = DemoProjectInitializer()
        project_id = initializer.initialize_demo_data()
        
        print(f"\n🎉 Demo project created successfully!")
        print(f"Project ID: {project_id}")
        print(f"You can now run scans against this project.")
        
    except Exception as e:
        print(f"\n💥 Failed to initialize demo project: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()