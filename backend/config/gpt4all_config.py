import os

GPT4ALL_CONFIG = {
    'model_path': os.getenv('GPT4ALL_MODEL_PATH', '/app/models'),
    # AI is now disabled by default - pattern analysis only
    'model_name': os.getenv('GPT4ALL_MODEL', 'disabled'),
    
    # Pattern-only analysis settings
    'use_ai_analysis': os.getenv('USE_AI_ANALYSIS', 'false').lower() == 'true',
    'pattern_analysis_only': True,  # Force pattern analysis only
    'max_logs_per_analysis': int(os.getenv('MAX_LOGS_ANALYSIS', '1000')),  # Can handle more logs now
    
    'available_models': [
        'orca-mini-3b-gguf2-q4_0.gguf',       # Fastest if AI needed
        'Meta-Llama-3-8B-Instruct.Q4_0.gguf'  # More accurate if AI needed
    ],
    
    # Pattern analysis is now primary method
    'enable_comprehensive_patterns': True,
    'pattern_confidence_threshold': 0.7,
    'success_detection_strict': True,
    
    # Success detection patterns
    'success_patterns': {
        'systemctl_patterns': [
            r'systemctl.*started.*successfully',
            r'systemctl.*enabled.*successfully', 
            r'systemctl.*restarted.*successfully',
            r'service.*started.*successfully',
            r'unit.*started.*successfully'
        ],
        'general_success_patterns': [
            r'successfully\s+completed',
            r'completed\s+successfully',
            r'operation\s+successful',
            r'deployment\s+successful'
        ],
        'validation_patterns': [
            r'validation\s+passed',
            r'checksum\s+verified',
            r'integrity\s+check\s+passed',
            r'all\s+tests\s+passed'
        ]
    },
    
    # Failure detection patterns
    'failure_patterns': {
        'service_failures': [
            r'failed\s+to\s+start',
            r'service\s+failed',
            r'systemctl.*failed',
            r'unit\s+failed'
        ],
        'network_failures': [
            r'connection\s+refused',
            r'connection\s+failed', 
            r'connection\s+timeout',
            r'network\s+unreachable'
        ],
        'system_failures': [
            r'permission\s+denied',
            r'command\s+not\s+found',
            r'file\s+not\s+found',
            r'fatal\s+error'
        ]
    },
    
    # Performance settings (for if AI is enabled)
    'ai_settings': {
        'max_tokens': 200,
        'temperature': 0.05,
        'timeout_seconds': 10,
        'enable_timeout': True
    }
}