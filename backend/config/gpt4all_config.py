import os

GPT4ALL_CONFIG = {
    'model_name': os.getenv('GPT4ALL_MODEL', 'orca-mini-3b-gguf2-q4_0.gguf'),
    'max_tokens': int(os.getenv('GPT4ALL_MAX_TOKENS', '1000')),
    'temperature': float(os.getenv('GPT4ALL_TEMPERATURE', '0.1')),
    'top_p': float(os.getenv('GPT4ALL_TOP_P', '0.9')),
    'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '50')),
    'enable_caching': os.getenv('ENABLE_ANALYSIS_CACHING', 'true').lower() == 'true'
}
