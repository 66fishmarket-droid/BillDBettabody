"""
Bill D'Bettabody - Backend Configuration
Central configuration for all backend services
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True') == 'True'
    PORT = int(os.getenv('PORT', 5000))
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Claude API
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'  # Sonnet 4
    CLAUDE_MAX_TOKENS = 4096
    
    # Make.com Webhook URLs
    WEBHOOKS = {
        # Client Management
        'check_client_exists': os.getenv('WEBHOOK_CHECK_CLIENT_EXISTS'),
        'post_user_upsert': os.getenv('WEBHOOK_USER_UPSERT'),
        'load_client_context': os.getenv('WEBHOOK_LOAD_CLIENT_CONTEXT'),
        
        # Contraindications
        'add_chronic_condition': os.getenv('WEBHOOK_ADD_CHRONIC_CONDITION'),
        'add_injury': os.getenv('WEBHOOK_ADD_INJURY'),
        'update_injury_status': os.getenv('WEBHOOK_UPDATE_INJURY_STATUS'),
        
        # Training Plans
        'full_training_block': os.getenv('WEBHOOK_FULL_TRAINING_BLOCK'),
        'populate_training_week': os.getenv('WEBHOOK_POPULATE_TRAINING_WEEK'),
        'session_update': os.getenv('WEBHOOK_SESSION_UPDATE'),
        
        # Developer & Admin
        'authenticate_developer': os.getenv('WEBHOOK_AUTHENTICATE_DEVELOPER'),
        'issue_log_updater': os.getenv('WEBHOOK_ISSUE_LOG_UPDATER'),
        
        # Communication
        'build_session_form_urls': os.getenv('WEBHOOK_BUILD_SESSION_FORM_URLS'),
        'daily_email_generator': os.getenv('WEBHOOK_DAILY_EMAIL_GENERATOR'),
    }
    
    # Session Management
    SESSION_TIMEOUT_MINUTES = 60
    MAX_CONVERSATION_LENGTH = 50  # messages
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOCS_DIR = os.path.join(BASE_DIR, '..', 'docs')
    BILL_INSTRUCTIONS_PATH = os.path.join(DOCS_DIR, 'GPT Instructions', 'Bill_Instructions_current.txt')
    SCENARIO_HELPER_PATH = os.path.join(DOCS_DIR, 'GPT Instructions', 'scenario_helper_instructions.txt')
    # Exercise Library paths
    EXERCISE_LIBRARY_QUICK_REF = os.path.join(DOCS_DIR, 'Exercise_Instructions', 'Exercise_Library_QuickRef_v2.txt')
    EXERCISE_LIBRARY_CANONICAL = os.path.join(DOCS_DIR, 'Exercise_Instructions', 'Exercise_Library_Canonical_v2_full.txt')

    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        
        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY not set")
        
        # Check critical webhooks
        critical_webhooks = [
            'check_client_exists',
            'load_client_context',
            'post_user_upsert'
        ]
        
        for webhook in critical_webhooks:
            if not cls.WEBHOOKS.get(webhook):
                errors.append(f"Critical webhook not configured: {webhook}")
        
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    TESTING = False
    # Production should override SECRET_KEY


class TestingConfig(Config):
    """Testing-specific configuration"""
    DEBUG = True
    TESTING = True
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'  # Use real model even in tests


# Configuration selector
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(config_name, DevelopmentConfig)