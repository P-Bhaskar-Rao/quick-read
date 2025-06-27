# embedding.py
import os
import vertexai
from vertexai.language_models import TextEmbeddingModel
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Vertex AI globally and once
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

# Ensure PROJECT_ID and REGION are set before initializing Vertex AI
if not PROJECT_ID or not REGION:
    logger.error("GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_REGION not set for Vertex AI initialization.")
    raise ValueError("Missing GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_REGION environment variables.")

logger.info(f'Initializing Vertex AI embeddings for project {PROJECT_ID} in region {REGION}...')
vertexai.init(project=PROJECT_ID, location=REGION)

# Initialize the embedding model
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
logger.info('Vertex AI embedding model (text-embedding-004) initialized.')


def get_embeddings(texts: list, batch_size: int = 20) -> list:
    """
    Get embeddings for a list of texts using Vertex AI
    
    Args:
        texts: List of text strings to embed
        batch_size: Number of texts to process in each batch
    
    Returns:
        List of embedding vectors
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            # Truncate texts to avoid API limits (8192 for text-embedding-004)
            truncated_batch = [text[:8000] for text in batch] 
            embeddings = embedding_model.get_embeddings(truncated_batch)
            all_embeddings.extend([emb.values for emb in embeddings])
        except Exception as e:
            logger.error(f"Error processing embedding batch {i//batch_size + 1}: {e}")
            # Add zero vectors for failed batch
            all_embeddings.extend([[0.0] * 768] * len(batch))
    
    return all_embeddings

def get_single_embedding(text: str) -> list:
    """
    Get embedding for a single text using Vertex AI
    
    Args:
        text: Text string to embed
    
    Returns:
        Embedding vector as list of floats
    """
    try:
        # Truncate text to avoid API limits (8192 for text-embedding-004)
        truncated_text = text[:8000] 
        embeddings = embedding_model.get_embeddings([truncated_text])
        return embeddings[0].values
    except Exception as e:
        logger.error(f"Error getting single embedding: {e}")
        return [0.0] * 768  # Return zero vector on error

def get_batch_embeddings(texts: list, batch_size: int = 20) -> list:
    """
    Public interface to batch-embed a list of texts using Vertex AI embeddings.
    Useful for document or webpage chunking.

    Args:
        texts (list): List of text strings to embed.
        batch_size (int): Batch size for API calls. Defaults to 20.

    Returns:
        List of 768-dim float vectors.
    """
    return get_embeddings(texts, batch_size=batch_size)


# For backward compatibility with existing code
class VertexAIEmbeddings:
    """Wrapper class to maintain compatibility with existing LangChain-style usage"""
    
    def __init__(self):
        # This will use the globally initialized embedding_model
        self.model = embedding_model
    
    def embed_documents(self, texts: list) -> list:
        """Embed a list of documents"""
        return get_embeddings(texts)
    
    def embed_query(self, text: str) -> list:
        """Embed a single query"""
        return get_single_embedding(text)


vertex_ai_embeddings_instance = VertexAIEmbeddings()