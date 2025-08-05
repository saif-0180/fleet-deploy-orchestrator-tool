import os
from typing import Optional

def select_optimal_model(available_memory_gb: Optional[float] = None) -> str:
    """
    Select the best model based on available resources
    """
    models = {
        'orca-mini-3b-gguf2-q4_0.gguf': {
            'size_gb': 2,
            'speed': 'fast',
            'quality': 'good'
        },
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf': {
            'size_gb': 4,
            'speed': 'medium',
            'quality': 'excellent'
        }
    }
    
    model_path = os.getenv('GPT4ALL_MODEL_PATH', '/app/models')
    available_models = [f for f in os.listdir(model_path) if f.endswith('.gguf')]
    
    # If specific memory constraint
    if available_memory_gb:
        for model, specs in models.items():
            if model in available_models and specs['size_gb'] <= available_memory_gb:
                return model
    
    # Default preference order
    preferred_order = ['orca-mini-3b-gguf2-q4_0.gguf', 'Meta-Llama-3-8B-Instruct.Q4_0.gguf']
    
    for model in preferred_order:
        if model in available_models:
            return model
    
    # Return first available model
    return available_models[0] if available_models else None
