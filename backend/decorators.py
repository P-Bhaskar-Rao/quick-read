"""
Decorators for common functionality
"""
from functools import wraps
from flask import jsonify, session
import logging
import time


logger = logging.getLogger(__name__)



def retry_on_rate_limit(max_retries=3, base_delay=2):
    """
    Decorator to retry Gemini API calls when rate-limited (HTTP 429)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "429" in str(e) or "Resource exhausted" in str(e):
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Gemini rate limit hit. Retrying in {delay} seconds (attempt {attempt+1})...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Unhandled Gemini error: {e}")
                        raise
            raise RuntimeError("Max retries exceeded due to rate limits.")
        return wrapper
    return decorator


def require_file_upload(f):
    """Decorator to ensure file is uploaded before processing"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        file_info = session.get('file_info', {})
        if not file_info:
            return jsonify({"error": "No file uploaded"}), 400
        return f(*args, **kwargs)
    return decorated_function

def handle_exceptions(operation_name):
    """Decorator for consistent exception handling"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"{operation_name} error: {e}")
                error_msg = f"Error in {operation_name.lower()}: {str(e)}"
                return jsonify({"error": error_msg}), 500
        return decorated_function
    return decorator

def validate_request_data(required_fields):
    """Decorator to validate required fields in request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            data = request.get_json() if request.is_json else {}
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator