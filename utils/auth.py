"""
utils/auth.py — Authentication utilities
Password hashing, CSRF tokens, session security
"""
import os
import secrets
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, request, abort
from functools import wraps


# ═══════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING (using werkzeug)
# ═══════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """Hash password using PBKDF2"""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return check_password_hash(password_hash, password)


# ═══════════════════════════════════════════════════════════════════════════
# CSRF TOKENS
# ═══════════════════════════════════════════════════════════════════════════

def generate_csrf_token() -> str:
    """Generate a CSRF token and store in session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf_token() -> bool:
    """Validate CSRF token from form/request"""
    if request.method in ['GET', 'HEAD', 'OPTIONS']:
        return True
    
    token = session.get('csrf_token', None)
    if not token:
        return False
    
    # Check POST data or headers
    request_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    
    if  not request_token:
        return False
    
    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, request_token)


def require_csrf(f):
    """Decorator to require valid CSRF token on POST/PUT/DELETE"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_csrf_token():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ═══════════════════════════════════════════════════════════════════════════
# SESSION HARDENING
# ═══════════════════════════════════════════════════════════════════════════

def setup_secure_session(app):
    """Configure session security settings"""
    # Allow secure cookies to be disabled for local development
    secure_cookies = os.getenv("SECURE_COOKIES", "False").lower() in ("true", "1", "yes")
    
    app.config.update(
        SESSION_COOKIE_SECURE=secure_cookies,  # Only send over HTTPS in production
        SESSION_COOKIE_HTTPONLY=True,  # No JS access
        SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SESSION_REFRESH_EACH_REQUEST=True,
    )


def set_secure_session(user: str, email: str):
    """Set secure session after login"""
    session.clear()
    session['user'] = user
    session['email'] = email
    session['created_at'] = secrets.token_hex(8)
    session.permanent = True
    
    # Generate CSRF token
    generate_csrf_token()


# ═══════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_email(email: str) -> bool:
    """Basic email validation"""
    # Very basic check - in production use email-validator library
    if not email or '@' not in email or '.' not in email:
        return False
    return len(email) <= 254


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, "Password valid"
