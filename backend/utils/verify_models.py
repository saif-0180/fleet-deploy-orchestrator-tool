#!/usr/bin/env python3

import os
import sys
from pathlib import Path

def verify_models():
    """Verify that models are properly installed"""
    model_path = os.getenv('GPT4ALL_MODEL_PATH', '/app/models')
    
    if not os.path.exists(model_path):
        print(f"❌ Model directory {model_path} does not exist")
        return False
    
    models = list(Path(model_path).glob('*.gguf'))
    
    if not models:
        print(f"❌ No .gguf models found in {model_path}")
        return False
    
    print(f"✅ Found {len(models)} models in {model_path}:")
    total_size = 0
    
    for model in models:
        size_mb = model.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  - {model.name} ({size_mb:.1f} MB)")
    
    print(f"Total model size: {total_size:.1f} MB ({total_size/1024:.1f} GB)")
    
    # Test model loading
    try:
        from gpt4all import GPT4All
        test_model = GPT4All(models[0].name, model_path=model_path)
        print(f"✅ Successfully loaded {models[0].name}")
        return True
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return False

if __name__ == "__main__":
    success = verify_models()
    sys.exit(0 if success else 1)
