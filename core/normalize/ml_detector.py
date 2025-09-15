"""
ML Framework detector module.
Provides functions to detect ML frameworks in Python code.
"""

import re
from typing import Dict, List, Set, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Define patterns for different ML frameworks
FRAMEWORK_PATTERNS = {
    'tensorflow': [
        r'import\s+tensorflow',
        r'from\s+tensorflow',
        r'import\s+tf\b',
        r'from\s+tf\b',
        r'tf\.keras'
    ],
    'pytorch': [
        r'import\s+torch',
        r'from\s+torch',
        r'nn\.Module',
        r'torch\.nn'
    ],
    'keras': [
        r'import\s+keras',
        r'from\s+keras'
    ],
    'scikit-learn': [
        r'import\s+sklearn',
        r'from\s+sklearn'
    ],
    'xgboost': [
        r'import\s+xgboost',
        r'from\s+xgboost',
        r'\bxgb\.',
        r'XGBClassifier',
        r'XGBRegressor',
        r'xgboost\.train',
        r'xgb\.train',
        r'XGBoost',
        r'Booster\(',
        r'DMatrix\(',
        r'xgboost\.Booster',
        r'xgboost\.DMatrix'
    ],
    'lightgbm': [
        r'import\s+lightgbm',
        r'from\s+lightgbm',
        r'\blgb\.',
        r'LGBMClassifier',
        r'LGBMRegressor'
    ],
    'huggingface': [
        r'import\s+transformers',
        r'from\s+transformers',
        r'AutoModel',
        r'AutoTokenizer',
        r'pipeline\('
    ],
    'langchain': [
        r'import\s+langchain',
        r'from\s+langchain'
    ],
    'jax': [
        r'import\s+jax',
        r'from\s+jax',
        r'flax'
    ],
    'onnx': [
        r'import\s+onnx',
        r'from\s+onnx'
    ],
    'mxnet': [
        r'import\s+mxnet',
        r'from\s+mxnet'
    ],
    'opencv': [
        r'import\s+cv2',
        r'from\s+cv2'
    ],
    'nltk': [
        r'import\s+nltk',
        r'from\s+nltk'
    ],
    'spacy': [
        r'import\s+spacy',
        r'from\s+spacy'
    ]
}

# Define patterns for model architectures
MODEL_PATTERNS = {
    'autoencoder': [
        r'\bautoencoder\b',
        r'\bencoder\b.*\bdecoder\b',
        r'\.encode\(',
        r'\.decode\(',
        r'encoder.*decoder',
        r'encoded.*decoded',
        r'latent_space',
        r'latent_dim',
        r'bottleneck\s+layer',
        r'reconstruction\s+loss',
        r'Autoencoder',
        r'VAE',
        r'variational\s+autoencoder'
    ],
    'transformer': [
        r'\btransformer\b',
        r'\battention\b',
        r'self-attention',
        r'multi-head'
    ],
    'cnn': [
        r'Conv[1-3]D',
        r'convolution',
        r'convolutional'
    ],
    'rnn': [
        r'\bRNN\b',
        r'\bLSTM\b',
        r'\bGRU\b',
        r'recurrent'
    ],
    'gan': [
        r'\bGAN\b',
        r'generative adversarial',
        r'generator.*discriminator'
    ],
    'bert': [
        r'\bBERT\b',
        r'bert-base',
        r'bert-large'
    ],
    'gpt': [
        r'\bGPT\b',
        r'GPT-2',
        r'GPT-3',
        r'GPT-4'
    ],
    'llm': [
        r'\bLLM\b',
        r'large language model',
        r'foundation model'
    ]
}

def detect_frameworks_in_file(file_path: Path) -> Dict[str, bool]:
    """
    Detect ML frameworks used in a file.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dictionary mapping framework names to boolean indicating presence
    """
    frameworks = {name: False for name in FRAMEWORK_PATTERNS.keys()}
    models = {name: False for name in MODEL_PATTERNS.keys()}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for frameworks
        for framework, patterns in FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    frameworks[framework] = True
                    break
        
        # Check for model architectures
        for model, patterns in MODEL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    models[model] = True
                    break
                    
        return {**frameworks, **models}
        
    except Exception as e:
        logger.warning(f"Could not analyze file {file_path}: {e}")
        return {**frameworks, **models}

def get_detected_ml_info(detected: Dict[str, bool]) -> Dict[str, List[str]]:
    """
    Format detection results into readable format.
    
    Args:
        detected: Dictionary mapping framework/model names to boolean indicating presence
        
    Returns:
        Dictionary with 'frameworks' and 'models' keys
    """
    frameworks_detected = [name for name, present in detected.items() 
                          if present and name in FRAMEWORK_PATTERNS]
    
    models_detected = [name for name, present in detected.items() 
                      if present and name in MODEL_PATTERNS]
    
    return {
        'frameworks': frameworks_detected,
        'models': models_detected
    }
