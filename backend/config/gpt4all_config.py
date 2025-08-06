import os

GPT4ALL_CONFIG = {
    'model_path': os.getenv('GPT4ALL_MODEL_PATH', '/app/models'),
    # Use smallest/fastest model by default for speed
    'model_name': os.getenv('GPT4ALL_MODEL', 'orca-mini-3b-gguf2-q4_0.gguf'),
    
    # Ultra-speed optimized settings
    'max_tokens': int(os.getenv('GPT4ALL_MAX_TOKENS', '200')),  # Very short for speed
    'temperature': float(os.getenv('GPT4ALL_TEMPERATURE', '0.05')),  # Very low for consistency
    'top_p': float(os.getenv('GPT4ALL_TOP_P', '0.5')),  # Very focused
    'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '10')),  # Minimal logs
    'enable_caching': os.getenv('ENABLE_ANALYSIS_CACHING', 'true').lower() == 'true',
    
    'available_models': [
        'orca-mini-3b-gguf2-q4_0.gguf',       # Primary - fastest
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf'  # Fallback - more accurate but slower
    ],
    
    # Aggressive speed optimization
    'quick_success_detection': True,
    'max_prompt_length': 300,         # Very short prompts
    'use_chat_session': False,        # Direct generate is faster
    'enable_timeout': True,           # Enable AI timeout
    'ai_timeout_seconds': 10,         # Very short timeout
    'prefer_pattern_analysis': True,  # Prefer fast pattern matching
    
    # Ultra-fast model settings
    'model_settings': {
        'orca-mini-3b-gguf2-q4_0.gguf': {
            'max_tokens': 150,           # Very short
            'temperature': 0.01,         # Minimal randomness
            'top_p': 0.3,               # Very focused
            'top_k': 5,                 # Minimal choices
            'repeat_penalty': 1.0,      # No penalty
            'prompt_style': 'ultra_simple'
        },
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf': {
            'max_tokens': 200,
            'temperature': 0.05,
            'top_p': 0.5,
            'top_k': 10,
            'repeat_penalty': 1.0,
            'prompt_style': 'simple_fast'
        }
    },
    
    # Performance limits
    'max_analysis_time_seconds': 15,   # Hard timeout
    'pattern_analysis_threshold': 0.6, # Use pattern analysis if confidence < 60%
    'success_confidence_threshold': 0.8, # High confidence for success fast-path
    'enable_enhanced_patterns': True,   # Use comprehensive pattern matching
    
    # Success detection optimization
    'comprehensive_success_patterns': True,  # Use all success patterns
    'validation_log_detection': True,        # Special handling for validation logs
    'implicit_success_detection': True,      # Detect implicit success
}