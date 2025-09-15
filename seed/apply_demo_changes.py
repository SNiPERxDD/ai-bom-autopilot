#!/usr/bin/env python3
"""
Script to apply scripted changes to demo project for rich diff demonstration
Implements changes like 8B→70B model upgrade and license modifications
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class DemoChangeApplicator:
    """Applies scripted changes to create rich diffs for demonstration"""
    
    def __init__(self, sample_project_path: str = "seed/sample_project"):
        self.sample_project_path = Path(sample_project_path)
        self.backup_path = Path("seed/sample_project_backup")
        self.changes_applied = []
        
    def backup_original_files(self):
        """Create backup of original files before making changes"""
        print("Creating backup of original files...")
        
        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)
        
        shutil.copytree(self.sample_project_path, self.backup_path)
        print(f"Backup created at: {self.backup_path}")
    
    def apply_model_upgrade_8b_to_70b(self):
        """Change LLaMA model from 8B to 70B parameters"""
        print("Applying model upgrade: 8B → 70B...")
        
        changes = [
            {
                "file": "models/model_config.json",
                "description": "Upgrade LLaMA model from 8B to 70B parameters",
                "changes": [
                    ("Llama-3.1-8B", "Llama-3.1-70B"),
                    ('"parameters": "8B"', '"parameters": "70B"'),
                    ('"version": "1.0.0"', '"version": "2.0.0"')
                ]
            },
            {
                "file": "train.py", 
                "description": "Update training script to use 70B model",
                "changes": [
                    ("meta-llama/Llama-3.1-8B", "meta-llama/Llama-3.1-70B"),
                    ("MODEL_NAME = \"meta-llama/Llama-3.1-8B\"", "MODEL_NAME = \"meta-llama/Llama-3.1-70B\"")
                ]
            },
            {
                "file": "README.md",
                "description": "Update documentation to reflect 70B model",
                "changes": [
                    ("LLaMA 3.1 8B", "LLaMA 3.1 70B"),
                    ("Llama-3.1-8B", "Llama-3.1-70B")
                ]
            },
            {
                "file": "config.yaml",
                "description": "Update config for 70B model",
                "changes": [
                    ("meta-llama/Llama-3.1-8B", "meta-llama/Llama-3.1-70B")
                ]
            }
        ]
        
        self._apply_file_changes(changes)
        self.changes_applied.extend(changes)
    
    def apply_license_modifications(self):
        """Apply license changes that should trigger policy violations"""
        print("Applying license modifications...")
        
        changes = [
            {
                "file": "models/model_config.json",
                "description": "Change BERT license from Apache-2.0 to GPL-3.0 (restrictive)",
                "changes": [
                    ('"license": "Apache-2.0"', '"license": "GPL-3.0"')
                ]
            },
            {
                "file": "datasets/dataset_manifest.yaml",
                "description": "Change dataset license to unknown",
                "changes": [
                    ('license: "Apache-2.0"', 'license: "unknown"'),
                    ('license: "CC BY-SA 4.0"', 'license: "proprietary"')
                ]
            },
            {
                "file": "tools/requirements.txt",
                "description": "Add new tool with restrictive license",
                "changes": [
                    ("# Development", "# New restrictive tool\nrestrictive-ml-lib==1.0.0  # GPL-3.0 license\n\n# Development")
                ]
            }
        ]
        
        self._apply_file_changes(changes)
        self.changes_applied.extend(changes)
    
    def apply_prompt_modifications(self):
        """Modify protected prompts to trigger policy violations"""
        print("Applying prompt modifications...")
        
        changes = [
            {
                "file": "prompts/system_prompt.txt",
                "description": "Modify protected system prompt",
                "changes": [
                    ("You are a helpful AI assistant", "You are an advanced AI system"),
                    ("Always be accurate, helpful", "Always prioritize efficiency over accuracy")
                ]
            },
            {
                "file": "prompts/qa_prompt.txt", 
                "description": "Modify protected QA prompt",
                "changes": [
                    ("based only on the information provided", "using any available knowledge"),
                    ("Keep your answer concise", "Provide detailed explanations")
                ]
            }
        ]
        
        self._apply_file_changes(changes)
        self.changes_applied.extend(changes)
    
    def add_new_dependencies(self):
        """Add new dependencies to trigger policy checks"""
        print("Adding new dependencies...")
        
        changes = [
            {
                "file": "requirements.txt",
                "description": "Add new dependencies with various licenses",
                "changes": [
                    ("# Jupyter notebook support", """# New AI/ML dependencies
tensorflow==2.14.0  # Apache-2.0
langchain==0.0.350  # MIT
chromadb==0.4.18  # Apache-2.0
pinecone-client==2.2.4  # proprietary

# Jupyter notebook support""")
                ]
            },
            {
                "file": "tools/model_utils.py",
                "description": "Add imports for new dependencies",
                "changes": [
                    ("import json", """import json
import tensorflow as tf
from langchain.llms import OpenAI
import chromadb""")
                ]
            }
        ]
        
        self._apply_file_changes(changes)
        self.changes_applied.extend(changes)
    
    def modify_dataset_versions(self):
        """Update dataset versions to trigger version drift detection"""
        print("Modifying dataset versions...")
        
        changes = [
            {
                "file": "datasets/dataset_manifest.yaml",
                "description": "Update dataset versions",
                "changes": [
                    ('version: "1.0.0"', 'version: "2.1.0"'),
                    ('version: "1.1.0"', 'version: "2.0.0"'),
                    ('size: "25000 samples"', 'size: "50000 samples"'),
                    ('size: "100k+ samples"', 'size: "150k+ samples"')
                ]
            },
            {
                "file": "data_processing.py",
                "description": "Update dataset loading code",
                "changes": [
                    ('dataset = load_dataset("imdb")', 'dataset = load_dataset("imdb", revision="v2.1.0")'),
                    ('dataset = load_dataset("squad")', 'dataset = load_dataset("squad", revision="v2.0.0")')
                ]
            }
        ]
        
        self._apply_file_changes(changes)
        self.changes_applied.extend(changes)
    
    def add_unknown_provider_models(self):
        """Add models from unknown providers to trigger policy violations"""
        print("Adding models from unknown providers...")
        
        # Create new model config with unknown provider
        new_model_config = {
            "name": "custom-ai-corp/proprietary-llm-v3",
            "type": "causal-lm", 
            "license": "proprietary",
            "provider": "custom-ai-corp",  # Unknown provider
            "version": "3.0.0",
            "parameters": "175B",
            "use_case": "general_purpose"
        }
        
        # Read existing model config
        model_config_path = self.sample_project_path / "models/model_config.json"
        with open(model_config_path, 'r') as f:
            config = json.load(f)
        
        # Add new model
        config["models"].append(new_model_config)
        
        # Write back
        with open(model_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Update train.py to reference new model
        changes = [
            {
                "file": "train.py",
                "description": "Add reference to unknown provider model",
                "changes": [
                    ('OPENAI_MODELS = ["gpt-4", "gpt-3.5-turbo"]', 
                     'OPENAI_MODELS = ["gpt-4", "gpt-3.5-turbo"]\nCUSTOM_MODELS = ["custom-ai-corp/proprietary-llm-v3"]')
                ]
            }
        ]
        
        self._apply_file_changes(changes)
        self.changes_applied.append({
            "file": "models/model_config.json",
            "description": "Added model from unknown provider",
            "changes": [("Added custom-ai-corp/proprietary-llm-v3", "")]
        })
    
    def _apply_file_changes(self, changes_list):
        """Apply a list of file changes"""
        for change in changes_list:
            file_path = self.sample_project_path / change["file"]
            
            if not file_path.exists():
                print(f"Warning: File {file_path} does not exist, skipping...")
                continue
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply changes
            for old_text, new_text in change["changes"]:
                if old_text in content:
                    content = content.replace(old_text, new_text)
                    print(f"  ✓ Applied change in {change['file']}: {old_text[:50]}...")
                else:
                    print(f"  ⚠ Change not found in {change['file']}: {old_text[:50]}...")
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def create_change_summary(self):
        """Create a summary of all changes applied"""
        summary_path = self.sample_project_path / "CHANGES.md"
        
        summary_content = f"""# Demo Changes Applied

Applied on: {datetime.now().isoformat()}

## Summary of Changes

This document summarizes the scripted changes applied to create a rich diff for ML-BOM Autopilot demonstration.

### Model Changes
- **LLaMA Model Upgrade**: Changed from 8B to 70B parameters (major version bump)
- **Unknown Provider**: Added model from custom-ai-corp (unknown provider)

### License Changes  
- **BERT License**: Changed from Apache-2.0 to GPL-3.0 (restrictive license)
- **Dataset Licenses**: Changed some to unknown/proprietary

### Prompt Changes
- **System Prompt**: Modified protected system prompt content
- **QA Prompt**: Modified protected question-answering prompt

### Dependency Changes
- **New Dependencies**: Added TensorFlow, LangChain, ChromaDB, Pinecone
- **Version Updates**: Updated dataset versions (minor and major bumps)

### Expected Policy Violations

These changes should trigger the following policy events:
1. `model_bump_major` - LLaMA 8B → 70B upgrade
2. `unapproved_license` - GPL-3.0 and proprietary licenses
3. `unknown_provider` - custom-ai-corp provider
4. `prompt_changed_protected_path` - System and QA prompt modifications
5. `missing_license` - Dependencies with unknown licenses

## Files Modified

"""
        
        for change in self.changes_applied:
            summary_content += f"- **{change['file']}**: {change['description']}\n"
        
        summary_content += f"""
## Restoration

To restore original files:
```bash
rm -rf {self.sample_project_path}
cp -r {self.backup_path} {self.sample_project_path}
```
"""
        
        with open(summary_path, 'w') as f:
            f.write(summary_content)
        
        print(f"Change summary written to: {summary_path}")
    
    def apply_all_changes(self):
        """Apply all scripted changes for comprehensive diff testing"""
        print("=== Applying All Demo Changes ===")
        
        # Create backup first
        self.backup_original_files()
        
        try:
            # Apply all change categories
            self.apply_model_upgrade_8b_to_70b()
            self.apply_license_modifications()
            self.apply_prompt_modifications()
            self.add_new_dependencies()
            self.modify_dataset_versions()
            self.add_unknown_provider_models()
            
            # Create summary
            self.create_change_summary()
            
            print("\n✅ All changes applied successfully!")
            print(f"Total files modified: {len(set(c['file'] for c in self.changes_applied))}")
            print("These changes should trigger multiple policy violations when scanned.")
            
        except Exception as e:
            print(f"\n❌ Error applying changes: {e}")
            print("You may need to restore from backup and try again.")
            raise
    
    def restore_original_files(self):
        """Restore original files from backup"""
        print("Restoring original files from backup...")
        
        if not self.backup_path.exists():
            print("❌ No backup found. Cannot restore.")
            return False
        
        if self.sample_project_path.exists():
            shutil.rmtree(self.sample_project_path)
        
        shutil.copytree(self.backup_path, self.sample_project_path)
        print("✅ Original files restored successfully!")
        return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply demo changes to sample project")
    parser.add_argument("--restore", action="store_true", help="Restore original files from backup")
    parser.add_argument("--project-path", default="seed/sample_project", help="Path to sample project")
    
    args = parser.parse_args()
    
    applicator = DemoChangeApplicator(args.project_path)
    
    if args.restore:
        applicator.restore_original_files()
    else:
        print("=== ML-BOM Autopilot Demo Change Applicator ===")
        print("This script will apply scripted changes to create rich diffs.")
        print("Changes include: model upgrades, license changes, prompt modifications, etc.")
        
        confirm = input("\nProceed with applying changes? (y/N): ")
        if confirm.lower() == 'y':
            applicator.apply_all_changes()
        else:
            print("Operation cancelled.")

if __name__ == "__main__":
    main()