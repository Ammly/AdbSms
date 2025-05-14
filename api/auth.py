"""
Authentication module for AdbSms API
"""
import os
import uuid
import functools
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
from api.app import db, logger

# Set default API key or generate a secure one if not set
API_KEY = os.getenv("ADBSMS_API_KEY", "dev-key-change-me-in-production")


class ApiKey:
    """Simple API key model for authentication"""
    def __init__(self, key=None, name=None):
        self.key = key or str(uuid.uuid4())
        self.name = name or "Default API Key"
        self.created_at = datetime.utcnow()


def require_api_key(f):
    """Decorator to enforce API key authentication"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth check in development mode if configured
        if current_app.config.get('SKIP_AUTH_IN_DEV') and current_app.debug:
            return f(*args, **kwargs)
            
        # Check for API key in header or query parameter
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            logger.warning(f"API request without key: {request.path}")
            return jsonify({
                "error": "Unauthorized", 
                "message": "Missing API key"
            }), 401
            
        if api_key != API_KEY:
            logger.warning(f"Invalid API key used: {api_key[:6]}...")
            return jsonify({
                "error": "Forbidden", 
                "message": "Invalid API key"
            }), 403
            
        # API key is valid, proceed
        return f(*args, **kwargs)
        
    return decorated_function


def generate_api_key(name=None):
    """Generate a new API key"""
    return ApiKey(name=name)