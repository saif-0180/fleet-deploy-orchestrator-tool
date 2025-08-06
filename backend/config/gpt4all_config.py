
import os

GPT4ALL_CONFIG = {
    'model_path': os.getenv('GPT4ALL_MODEL_PATH', '/app/models'),
    # Use faster model by default for quicker responses
    'model_name': os.getenv('GPT4ALL_MODEL', 'orca-mini-3b-gguf2-q4_0.gguf'),
    
    # Optimized settings for speed
    'use_ai_analysis': os.getenv('USE_AI_ANALYSIS', 'false').lower() == 'true',
    'pattern_analysis_only': False,  # Allow AI for unclear cases only
    'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '100')),  # Reduced for speed
    
    'available_models': [
        'orca-mini-3b-gguf2-q4_0.gguf',       # Fastest model (2GB, ~5-15 sec)
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf'  # Better quality (4GB, ~15-30 sec)
    ],
    
    # Enhanced pattern detection
    'enable_comprehensive_patterns': True,
    'pattern_confidence_threshold': 0.8,
    'success_detection_strict': False,  # More lenient for better accuracy
    
    # Deployment type detection
    'deployment_type_detection': True,
    'auto_categorization': True,
    
    # Performance settings optimized for speed
    'ai_settings': {
        'max_tokens': 150,      # Reduced for faster response
        'temperature': 0.1,     # Lower for consistent results
        'timeout_seconds': 30,  # Reduced timeout
        'enable_timeout': True,
        'use_ai_only_when_unclear': True  # AI only as fallback
    }
}
