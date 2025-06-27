class GeminiRateLimitError(Exception):
    """Raised when Gemini API hits rate limit (429)"""
    pass

class GeminiAPIError(Exception):
    """Raised for other Gemini API errors"""
    pass
