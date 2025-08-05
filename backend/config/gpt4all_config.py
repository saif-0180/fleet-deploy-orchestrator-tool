import os

GPT4ALL_CONFIG = {
    'model_path': os.getenv('GPT4ALL_MODEL_PATH', '/app/models'),
    # Switch to the better Llama-3 model
    'model_name': os.getenv('GPT4ALL_MODEL', 'Meta-Llama-3-8B-Instruct.Q4_0.gguf'),
    'max_tokens': int(os.getenv('GPT4ALL_MAX_TOKENS', '1500')),
    'temperature': float(os.getenv('GPT4ALL_TEMPERATURE', '0.2')),  # Slightly higher for creativity
    'top_p': float(os.getenv('GPT4ALL_TOP_P', '0.9')),
    'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '50')),
    'enable_caching': os.getenv('ENABLE_ANALYSIS_CACHING', 'true').lower() == 'true',
    'available_models': [
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf',  # Primary choice - better instruction following
        'orca-mini-3b-gguf2-q4_0.gguf'         # Fallback - smaller but less capable
    ],
    # Model-specific settings
    'model_settings': {
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf': {
            'max_tokens': 1500,
            'temperature': 0.2,
            'top_p': 0.9,
            'repeat_penalty': 1.0,
            'prompt_style': 'llama3'
        },
        'orca-mini-3b-gguf2-q4_0.gguf': {
            'max_tokens': 800,
            'temperature': 0.1,
            'top_p': 0.8,
            'repeat_penalty': 1.1,
            'prompt_style': 'simple'
        }
    }
}


# import os

# GPT4ALL_CONFIG = {
#     'model_path': os.getenv('GPT4ALL_MODEL_PATH', '/app/models'),
#     'model_name': os.getenv('GPT4ALL_MODEL', 'orca-mini-3b-gguf2-q4_0.gguf'),
#     'max_tokens': int(os.getenv('GPT4ALL_MAX_TOKENS', '1000')),
#     'temperature': float(os.getenv('GPT4ALL_TEMPERATURE', '0.1')),
#     'top_p': float(os.getenv('GPT4ALL_TOP_P', '0.9')),
#     'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '50')),
#     'enable_caching': os.getenv('ENABLE_ANALYSIS_CACHING', 'true').lower() == 'true',
#     'available_models': [
#         'orca-mini-3b-gguf2-q4_0.gguf',
#         'Meta-Llama-3-8B-Instruct.Q4_0.gguf'
#     ]
# }
