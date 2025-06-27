# embed_pdf_to_cloudsql.py
"""
Updated embedding service that works with the simplified schema
Handles both PDF and URL content embedding to Cloud SQL with pgvector
"""
import psycopg2
import psycopg2.extras
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os
import json

# Google Cloud imports
from google.cloud import storage

# Local imports
from embedding import  get_single_embedding
from database_manager import DatabaseManager
from database_operations import DatabaseServices
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)

def create_tables_if_not_exists(db_manager: DatabaseManager):
    """Create all required tables using the simplified schema"""
    try:
        # Enable pgvector extension
        db_manager.execute_query("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create documents table
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS documents (
                file_id VARCHAR(255) PRIMARY KEY,
                original_filename VARCHAR(500),
                source_type VARCHAR(10) NOT NULL CHECK (source_type IN ('pdf', 'url')),
                source_path TEXT,
                file_size BIGINT,
                public_url TEXT,
                content_hash VARCHAR(64),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create chunks table
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_id VARCHAR(255) NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                chunk_metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_id, chunk_index)
            );
        """)
        
        # Create embeddings table
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id UUID PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                embedding VECTOR(768),
                model_name VARCHAR(100) DEFAULT 'textembedding-gecko',
                embedding_dim INTEGER DEFAULT 768,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes
        db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
        """)
        
        db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def process_pdf_content(
    file_id: str,
    pdf_path: str,
    db_manager: DatabaseManager,
    pdf_loader,
    original_filename: str,
    file_size: int = None,
    public_url: str = None
) -> bool:
    """
    Complete PDF processing pipeline:
    1. Load PDF and extract text
    2. Split into chunks
    3. Store chunks (for summarization)
    4. Generate and store embeddings (for QA)
    """
    try:
        logger.info(f"Starting PDF processing for file_id: {file_id}")
        
        # Initialize database services
        db_services = DatabaseServices(db_manager)
        
        # Load PDF documents from Cloud Storage
        docs = pdf_loader.load(blob_name=pdf_path)
        if not docs:
            logger.warning(f"No documents loaded for {pdf_path}")
            return False

        # Extract content and create chunks
        all_chunks = []
        for i, doc in enumerate(docs):
            page_content = doc.page_content
            metadata = doc.metadata
            
            # Split content into smaller chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # Larger chunks for better context
                chunk_overlap=100
            )
            chunks_on_page = text_splitter.split_text(page_content) 
            
            for chunk in chunks_on_page:
                all_chunks.append({
                    "content": chunk,
                    "page_number": metadata.get('page', i) + 1,
                    "metadata": {
                        "page": metadata.get('page', i) + 1,
                        "source": "pdf"
                    }
                })

        if not all_chunks:
            logger.warning(f"No chunks generated for {pdf_path}")
            return False

        # Generate embeddings for all chunks
        texts_to_embed = [chunk["content"] for chunk in all_chunks]
        embeddings = get_batch_embeddings_with_retry(texts_to_embed)

        if not embeddings or len(embeddings) != len(all_chunks):
            logger.error(f"Mismatch between chunks and embeddings for {file_id}")
            return False

        # Process document using database services
        success = db_services.process_document(
            file_id=file_id,
            filename=original_filename,
            source_type='pdf',
            source_path=pdf_path,
            chunks=all_chunks,
            embeddings=embeddings,
            file_size=file_size,
            public_url=public_url,
            metadata={'total_pages': len(docs), 'total_chunks': len(all_chunks)}
        )

        if success:
            logger.info(f"Successfully processed PDF {file_id} with {len(all_chunks)} chunks")
        else:
            logger.error(f"Failed to process PDF {file_id}")
            
        return success
            
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {e}")
        return False

def process_url_content(
    file_id: str,
    url: str,
    content: str,
    db_manager: DatabaseManager,
    title: str = None
) -> bool:
    """
    Complete URL processing pipeline:
    1. Split content into chunks
    2. Store chunks (for summarization)
    3. Generate and store embeddings (for QA)
    """
    try:
        logger.info(f"Starting URL processing for file_id: {file_id}")
        
        # Initialize database services
        db_services = DatabaseServices(db_manager)
        
        # Split content into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunk_texts = text_splitter.split_text(content)
        
        if not chunk_texts:
            logger.warning(f"No chunks generated for URL {url}")
            return False
        
        # Create chunk objects
        all_chunks = []
        for i, chunk_text in enumerate(chunk_texts):
            all_chunks.append({
                "content": chunk_text,
                "metadata": {
                    "chunk_index": i,
                    "source": "url",
                    "url": url
                }
            })

        # Generate embeddings for all chunks
        embeddings = get_batch_embeddings_with_retry(chunk_texts)

        if not embeddings or len(embeddings) != len(all_chunks):
            logger.error(f"Mismatch between chunks and embeddings for {file_id}")
            return False

        # Process document using database services
        success = db_services.process_document(
            file_id=file_id,
            filename=title or url,
            source_type='url',
            source_path=url,
            chunks=all_chunks,
            embeddings=embeddings,
            metadata={'url': url, 'total_chunks': len(all_chunks)}
        )

        if success:
            logger.info(f"Successfully processed URL {file_id} with {len(all_chunks)} chunks")
        else:
            logger.error(f"Failed to process URL {file_id}")
            
        return success
            
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        return False

def search_similar_content(
    query: str, 
    file_id: str, 
    limit: int, 
    db_manager: DatabaseManager
) -> List[Dict]:
    """
    Search for similar content using vector similarity
    """
    try:
        db_services = DatabaseServices(db_manager)
        
        # Generate query embedding
        query_embedding = get_single_embedding(query)
        if not query_embedding:
            logger.warning("Failed to generate embedding for query")
            return []

        # Search for similar chunks
        results = db_services.embeddings.similarity_search(
            query_embedding=query_embedding,
            file_id=file_id,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching similar content for file {file_id}: {e}")
        return []

# Add these functions to the end of updated_embedding_service.py

def get_content_for_summary(file_id: str, db_manager: DatabaseManager) -> List[Dict]:
    """
    ✅ CORRECT: Get all RAW TEXT CHUNKS for a document to generate summary
    This uses raw text chunks, NOT embeddings - which is the correct approach
    """
    try:
        db_services = DatabaseServices(db_manager)
        
        # Get all chunks for the document (raw text, not embeddings)
        query = """
            SELECT c.content, c.chunk_metadata, c.chunk_index 
            FROM chunks c 
            WHERE c.file_id = %s 
            ORDER BY c.chunk_index
        """
        
        results = db_manager.execute_query(query, (file_id,), fetch_results=True)

        
        if not results:
            logger.warning(f"No chunks found for file_id: {file_id}")
            return []
        
        # Convert to list of dictionaries
        chunks_data = []
        for row in results:
            chunks_data.append({
                'content': row[0],
                'metadata': row[1] if row[1] else {},
                'chunk_index': row[2]
            })
        
        logger.info(f"Retrieved {len(chunks_data)} chunks for summarization from file_id: {file_id}")
        return chunks_data
        
    except Exception as e:
        logger.error(f"Error getting content for summary from file {file_id}: {e}")
        return []

def get_batch_embeddings_with_retry(texts: List[str], max_retries: int = 3) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts with retry logic
    """
    try:
        from embedding import get_batch_embeddings
        
        for attempt in range(max_retries):
            try:
                embeddings = get_batch_embeddings(texts)
                if embeddings and len(embeddings) == len(texts):
                    return embeddings
                else:
                    logger.warning(f"Batch embedding attempt {attempt + 1} returned incomplete results")
                    
            except Exception as e:
                logger.warning(f"Batch embedding attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                
        return []
        
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        return []

def delete_file_embeddings(file_id: str, db_manager: DatabaseManager) -> bool:
    """
    Delete all embeddings and chunks for a specific file
    """
    try:
        db_services = DatabaseServices(db_manager)
        
        # Delete embeddings (will cascade delete due to foreign key)
        delete_embeddings_query = """
            DELETE FROM embeddings 
            WHERE chunk_id IN (
                SELECT chunk_id FROM chunks WHERE file_id = %s
            )
        """
        db_manager.execute_query(delete_embeddings_query, (file_id,))
        
        # Delete chunks (will cascade delete embeddings if not already deleted)
        delete_chunks_query = "DELETE FROM chunks WHERE file_id = %s"
        db_manager.execute_query(delete_chunks_query, (file_id,))
        
        # Delete document record
        delete_doc_query = "DELETE FROM documents WHERE file_id = %s"
        db_manager.execute_query(delete_doc_query, (file_id,))
        
        logger.info(f"Successfully deleted all data for file_id: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting embeddings for file {file_id}: {e}")
        return False

# Alias for backward compatibility with app.py
def embed_pdf_to_cloudsql(file_id: str, pdf_path: str, db_manager: DatabaseManager, 
                         pdf_loader, original_filename: str = None, 
                         file_size: int = None, public_url: str = None) -> bool:
    """
    Backward compatibility function that calls the new process_pdf_content
    """
    return process_pdf_content(
        file_id=file_id,
        pdf_path=pdf_path,
        db_manager=db_manager,
        pdf_loader=pdf_loader,
        original_filename=original_filename or pdf_path,
        file_size=file_size,
        public_url=public_url
    )

