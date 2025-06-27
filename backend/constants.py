"""
Application constants to reduce magic numbers and repeated strings
"""
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 20
DEFAULT_EMBEDDING_DIMENSION = 768
DEFAULT_SIMILARITY_LIMIT = 5
DEFAULT_SUMMARIZATION_LIMIT = 20
DEFAULT_TEMPERATURE_SUMMARIZATION = 0.5
DEFAULT_TEMPERATURE_QA = 0.3
DEFAULT_TEMPERATURE_SUGGESTIONS = 0.7
MAX_TEXT_LENGTH = 8000
MAX_RETRIES = 3
SUPPORTED_FILE_EXTENSIONS = ['.pdf']
DEFAULT_QUESTIONS = [
    "What are the main points of this document?",
    "Can you explain the key findings?", 
    "What are the conclusions?",
    "Are there any recommendations mentioned?"
]