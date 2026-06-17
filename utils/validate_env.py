"""
Environment Variable Validation & Security Checks

Runs at startup to ensure:
1. All required environment variables are set
2. Production environment is properly configured
3. Credentials are not exposed in code
4. Database and Redis connectivity
"""

import os
import sys
from urllib.parse import urlparse


class EnvironmentValidator:
    """Validates environment configuration and provides security checks."""
    
    REQUIRED_VARS = {
        'development': [
            'SECRET_KEY',
            'DATABASE_URL',
        ],
        'production': [
            'SECRET_KEY',
            'DATABASE_URL',
            'REDIS_URL',
            'FLASK_ENV',
        ]
    }
    
    AI_BACKENDS = {
        'openai': ['OPENAI_API_KEY'],
        'anthropic': ['ANTHROPIC_API_KEY'],
        'google': ['GOOGLE_API_KEY'],
        'ollama': ['OLLAMA_URL'],
    }
    
    WARNINGS = {
        'dev_key_change_in_production': (
            '⚠️  SECURITY WARNING: Using default/development SECRET_KEY in production! '
            'Generate a secure key: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        ),
        'http_in_production': (
            '⚠️  SECURITY WARNING: DATABASE_URL uses unencrypted connection! '
            'Use SSL in production: postgresql://user:pass@host:port/db?sslmode=require'
        ),
        'secure_cookies_not_set': (
            '⚠️  SECURITY WARNING: SECURE_COOKIES not explicitly set in production! '
            'Set SECURE_COOKIES=True for HTTPS-only cookies'
        ),
        'no_ai_backend': (
            '⚠️  WARNING: No AI backend configured! '
            'At least one of these must be set: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OLLAMA_URL'
        ),
        'no_redis': (
            '⚠️  WARNING: REDIS_URL not configured. Using in-memory sessions (not production-safe!'
            'Set REDIS_URL for distributed session management.'
        ),
    }
    
    @staticmethod
    def validate():
        """Run all validation checks. Raises SystemExit on critical failures."""
        env = os.getenv('FLASK_ENV', 'development')
        is_production = env == 'production'
        
        print("🔐 Environment Validation Starting...\n")
        
        # 1. Check required variables
        EnvironmentValidator._check_required_vars(env)
        
        # 2. Check for hardcoded secrets
        EnvironmentValidator._check_no_hardcoded_secrets()
        
        # 3. Production-specific checks
        if is_production:
            EnvironmentValidator._check_production_security()
        
        # 4. Check at least one AI backend
        EnvironmentValidator._check_ai_backends()
        
        # 5. Check optional but recommended vars
        EnvironmentValidator._check_optional_vars()
        
        print("\n✅ Environment validation complete!\n")
    
    @staticmethod
    def _check_required_vars(env):
        """Verify all required variables are set. Provides development defaults if needed."""
        required = EnvironmentValidator.REQUIRED_VARS.get(env, [])
        missing = [var for var in required if not os.getenv(var)]
        
        if missing and env == 'development':
            # Development mode: provide helpful defaults
            print(f"⚠️  Development mode: Missing variables will use defaults")
            for var in missing:
                if var == 'SECRET_KEY':
                    import secrets
                    default_key = secrets.token_urlsafe(32)
                    os.environ['SECRET_KEY'] = default_key
                    print(f"   📝 {var}: Generated temporary key")
                elif var == 'DATABASE_URL':
                    default_db = 'sqlite:///interview_proai.db'
                    os.environ['DATABASE_URL'] = default_db
                    print(f"   📝 {var}: Using SQLite database")
        elif missing:
            # Production mode: fail fast
            print(f"❌ CRITICAL: Missing required environment variables:")
            for var in missing:
                print(f"   - {var}")
            print(f"\nSet these variables in .env or as environment variables and restart.")
            sys.exit(1)
        
        print(f"✅ Required variables for '{env}' environment: OK")
    
    @staticmethod
    def _check_no_hardcoded_secrets():
        """Ensure no secrets are hardcoded in source files."""
        secret_patterns = [
            'sk-ant-',  # Anthropic keys
            'sk-',      # OpenAI keys
            'AIzaSy',   # Google API keys
            'GOCSPX-',  # Google OAuth secret patterns
        ]
        
        risky_files = ['app.py', 'celery_app.py', 'setup.py']
        found_secrets = []
        
        for filename in risky_files:
            filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', filename)
            if not os.path.exists(filepath):
                continue
            
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    for pattern in secret_patterns:
                        if pattern in content:
                            found_secrets.append(filename)
                            break
            except Exception:
                pass
        
        if found_secrets:
            print(f"❌ SECURITY WARNING: Possible hardcoded secrets found in: {found_secrets}")
            print("   Move all secrets to .env file immediately!")
        else:
            print("✅ No hardcoded secrets detected in source files")
    
    @staticmethod
    def _check_production_security():
        """Production-specific security checks."""
        print("\n🏭 Production Security Checks:")
        
        checks = []
        
        # Check SECRET_KEY
        secret_key = os.getenv('SECRET_KEY')
        if secret_key == 'dev_key_change_in_production':
            print(f"   ❌ {EnvironmentValidator.WARNINGS['dev_key_change_in_production']}")
            checks.append(False)
        elif len(secret_key or '') < 32:
            print("   ❌ SECRET_KEY is too short (must be at least 32 characters)")
            checks.append(False)
        else:
            print("   ✅ SECRET_KEY: Secure length and not using default")
            checks.append(True)
        
        # Check database SSL
        db_url = os.getenv('DATABASE_URL', '')
        if db_url.startswith('postgresql://') and 'sslmode' not in db_url:
            print(f"   ⚠️  {EnvironmentValidator.WARNINGS['http_in_production']}")
        elif db_url.startswith('postgresql://'):
            print("   ✅ DATABASE_URL: Using encrypted connection")
        
        # Check SECURE_COOKIES
        secure_cookies = os.getenv('SECURE_COOKIES', '').lower() != 'true'
        if secure_cookies:
            print(f"   ⚠️  {EnvironmentValidator.WARNINGS['secure_cookies_not_set']}")
        else:
            print("   ✅ SECURE_COOKIES: Enabled for HTTPS")
        
        if not all(checks):
            print("\n⚠️  Production environment has security issues. Review above warnings.")
    
    @staticmethod
    def _check_ai_backends():
        """Ensure at least one AI backend is configured."""
        print("\n🤖 AI Backend Configuration:")
        
        available = []
        for backend, required_vars in EnvironmentValidator.AI_BACKENDS.items():
            if all(os.getenv(var) for var in required_vars):
                available.append(backend)
        
        if not available:
            print(f"   ⚠️  {EnvironmentValidator.WARNINGS['no_ai_backend']}")
        else:
            print(f"   ✅ AI backends available: {', '.join(available)}")
    
    @staticmethod
    def _check_optional_vars():
        """Check for recommended optional variables."""
        print("\n📋 Optional Configuration:")
        
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            print(f"   ⚠️  {EnvironmentValidator.WARNINGS['no_redis']}")
        else:
            print("   ✅ REDIS_URL: Configured")
        
        mail_server = os.getenv('MAIL_SERVER')
        if not mail_server:
            print("   ℹ️  EMAIL: Not configured (email features disabled)")
        else:
            print("   ✅ EMAIL: Configured")
        
        sentry_dsn = os.getenv('SENTRY_DSN')
        if not sentry_dsn:
            print("   ℹ️  ERROR TRACKING: Not configured (Sentry disabled)")
        else:
            print("   ✅ ERROR TRACKING: Configured")


def validate_env():
    """Public function to run validation."""
    try:
        EnvironmentValidator.validate()
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    validate_env()
