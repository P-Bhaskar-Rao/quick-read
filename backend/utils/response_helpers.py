"""
Utility functions to reduce code repetition in API responses
"""
from flask import jsonify, session
import logging

logger = logging.getLogger(__name__)

def validate_file_info():
    """Validate that file_info exists in session"""
    file_info = session.get('file_info', {})
    if not file_info:
        return None, jsonify({"error": "No file uploaded"}), 400
    return file_info, None, None

def handle_api_error(error, operation_name):
    """Standardized error handling for API endpoints"""
    logger.error(f"{operation_name} error: {error}")
    error_msg = f"Error in {operation_name.lower()}: {str(error)}"
    return jsonify({"error": error_msg}), 500

def get_content_for_processing(file_info, content_type="summarization"):
    """Get content based on file type for processing"""
    if file_info.get('content_type') == 'url':
        content = file_info.get('url_content', '')
        if not content:
            return None, f"No content available for {content_type}"
        return content[:8000] if len(content) > 8000 else content, None
    
    elif file_info.get('content_type') == 'pdf':
        file_id = file_info.get('file_id')
        if not file_id:
            return None, "No file ID found"
        return file_id, None
    
    return None, f"Unsupported content type for {content_type}"