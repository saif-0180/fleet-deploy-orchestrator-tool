import os

GPT4ALL_CONFIG = {
    'model_path': os.getenv('GPT4ALL_MODEL_PATH', '/app/models'),
    # Use Llama-3 for better accuracy, but with speed optimizations
    'model_name': os.getenv('GPT4ALL_MODEL', 'Meta-Llama-3-8B-Instruct.Q4_0.gguf'),
    
    # Speed-optimized settings
    'max_tokens': int(os.getenv('GPT4ALL_MAX_TOKENS', '400')),  # Reduced from 1500
    'temperature': float(os.getenv('GPT4ALL_TEMPERATURE', '0.1')),  # Lower for faster, focused output
    'top_p': float(os.getenv('GPT4ALL_TOP_P', '0.8')),  # Reduced for speed
    'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '20')),  # Reduced
    'enable_caching': os.getenv('ENABLE_ANALYSIS_CACHING', 'true').lower() == 'true',
    
    'available_models': [
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf',  # Primary - good balance of speed/accuracy
        'orca-mini-3b-gguf2-q4_0.gguf'         # Fallback - very fast but less accurate
    ],
    
    # Speed optimization settings
    'quick_success_detection': True,  # Skip AI for obvious successes
    'max_prompt_length': 800,         # Limit prompt size for speed
    'use_chat_session': False,        # Direct generate is faster
    
    # Model-specific optimized settings
    'model_settings': {
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf': {
            'max_tokens': 400,
            'temperature': 0.1,
            'top_p': 0.8,
            'repeat_penalty': 1.0,
            'prompt_style': 'llama3_fast'  # Simplified prompting
        },
        'orca-mini-3b-gguf2-q4_0.gguf': {
            'max_tokens': 300,
            'temperature': 0.05,
            'top_p': 0.7,
            'repeat_penalty': 1.0,
            'prompt_style': 'simple_fast'
        }
    },
    
    # Performance thresholds
    'max_analysis_time_seconds': 10,  # Timeout for analysis
    'enable_pattern_fallback': True,   # Use pattern matching if AI is slow
}