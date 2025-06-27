import uuid
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    """Service class for document-related database operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_document(self, file_id: str, filename: str, source_type: str, 
                       source_path: str, file_size: int = None, 
                       public_url: str = None, metadata: dict = None) -> bool:
        """Create a new document record"""
        try:
            # Generate content hash for duplicate detection
            content_hash = hashlib.sha256(f"{filename}_{source_path}".encode()).hexdigest()
            
            query = """
                INSERT INTO documents (file_id, original_filename, source_type, source_path, 
                                     file_size, public_url, content_hash, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_id) DO UPDATE SET
                    original_filename = EXCLUDED.original_filename,
                    source_path = EXCLUDED.source_path,
                    file_size = EXCLUDED.file_size,
                    public_url = EXCLUDED.public_url,
                    content_hash = EXCLUDED.content_hash,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            self.db.execute_query(query, (
                file_id, filename, source_type, source_path, 
                file_size, public_url, content_hash, 
                json.dumps(metadata) if metadata else None
            ))
            
            logger.info(f"Document created: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating document {file_id}: {e}")
            return False
    
    def get_document(self, file_id: str) -> Optional[Dict]:
        """Get document metadata by file_id"""
        try:
            query = "SELECT * FROM documents WHERE file_id = %s"
            result = self.db.execute_query(query, (file_id,), fetch_results=True)
            
            if result:
                doc = result[0]
                return {
                    'file_id': doc[0],
                    'original_filename': doc[1],
                    'source_type': doc[2],
                    'source_path': doc[3],
                    'file_size': doc[4],
                    'public_url': doc[5],
                    'content_hash': doc[6],
                    'metadata': json.loads(doc[7]) if doc[7] else {},
                    'created_at': doc[8],
                    'updated_at': doc[9]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {file_id}: {e}")
            return None
    
    def list_documents(self, source_type: str = None, limit: int = 100) -> List[Dict]:
        """List all documents with optional filtering"""
        try:
            if source_type:
                query = """
                    SELECT file_id, original_filename, source_type, file_size, created_at 
                    FROM documents 
                    WHERE source_type = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                params = (source_type, limit)
            else:
                query = """
                    SELECT file_id, original_filename, source_type, file_size, created_at 
                    FROM documents 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                params = (limit,)
            
            results = self.db.execute_query(query, params, fetch_results=True)
            
            documents = []
            for row in results:
                documents.append({
                    'file_id': row[0],
                    'original_filename': row[1],
                    'source_type': row[2],
                    'file_size': row[3],
                    'created_at': row[4]
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    def delete_document(self, file_id: str) -> bool:
        """Delete document and all related data (cascades to chunks and embeddings)"""
        try:
            query = "DELETE FROM documents WHERE file_id = %s"
            rows_affected = self.db.execute_query(query, (file_id,))
            
            logger.info(f"Document deleted: {file_id} ({rows_affected} rows)")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Error deleting document {file_id}: {e}")
            return False


class ChunkService:
    """Service class for chunk-related database operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_chunks(self, file_id: str, chunks: List[Dict]) -> List[str]:
        """
        Create multiple chunks for a document
        Returns list of chunk_ids for embedding generation
        """
        try:
            # Delete existing chunks first (cascades to embeddings)
            self.db.execute_query("DELETE FROM chunks WHERE file_id = %s", (file_id,))
            
            # Insert new chunks
            query = """
                INSERT INTO chunks (file_id, chunk_index, content, chunk_metadata)
                VALUES (%s, %s, %s, %s)
                RETURNING chunk_id
            """
            
            chunk_ids = []
            for i, chunk in enumerate(chunks):
                content = chunk.get('content', chunk.get('text', ''))
                metadata = chunk.get('metadata', {})
                
                # Add token count and other useful metadata
                metadata.update({
                    'token_count': len(content.split()),
                    'char_count': len(content),
                    'page_number': chunk.get('page_number'),
                    'section': chunk.get('section')
                })
                
                result = self.db.execute_query(query, (
                    file_id, i, content, json.dumps(metadata)
                ), fetch_results=True)
                
                if result:
                    chunk_ids.append(str(result[0][0]))
            
            logger.info(f"Created {len(chunks)} chunks for document {file_id}")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"Error creating chunks for {file_id}: {e}")
            return []
    
    def get_chunks(self, file_id: str, limit: int = None) -> List[Dict]:
        """Get all chunks for a document (used for summarization)"""
        try:
            query = """
                SELECT chunk_id, chunk_index, content, chunk_metadata 
                FROM chunks 
                WHERE file_id = %s 
                ORDER BY chunk_index
            """
            
            params = (file_id,)
            if limit:
                query += " LIMIT %s"
                params = (file_id, limit)
            
            results = self.db.execute_query(query, params, fetch_results=True)
            
            chunks = []
            for row in results:
                chunks.append({
                    'chunk_id': str(row[0]),
                    'chunk_index': row[1],
                    'content': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {}
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting chunks for {file_id}: {e}")
            return []
    
    def get_chunk_content_for_summary(self, file_id: str) -> str:
        """Get all chunk content concatenated for summarization"""
        try:
            query = """
                SELECT content 
                FROM chunks 
                WHERE file_id = %s 
                ORDER BY chunk_index
            """
            
            results = self.db.execute_query(query, (file_id,), fetch_results=True)
            
            # Concatenate all chunks with newlines
            full_content = '\n\n'.join([row[0] for row in results])
            return full_content
            
        except Exception as e:
            logger.error(f"Error getting content for summary {file_id}: {e}")
            return ""


class EmbeddingService:
    """Service class for embedding-related database operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def store_embeddings(self, chunks_with_embeddings: List[Dict], 
                        model_name: str = 'textembedding-gecko') -> bool:
        """Store embeddings for multiple chunks"""
        try:
            query = """
                INSERT INTO embeddings (chunk_id, embedding, model_name, embedding_dim)
                VALUES (%s, %s::vector, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model_name = EXCLUDED.model_name,
                    embedding_dim = EXCLUDED.embedding_dim
            """
            
            success_count = 0
            for item in chunks_with_embeddings:
                try:
                    chunk_id = item['chunk_id']
                    embedding = item['embedding']
                    
                    # Format embedding for pgvector
                    if isinstance(embedding, list) and len(embedding) > 0:
                        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                        
                        self.db.execute_query(query, (
                            chunk_id, embedding_str, model_name, len(embedding)
                        ))
                        success_count += 1
                    else:
                        logger.warning(f"Invalid embedding for chunk {chunk_id}")
                        
                except Exception as e:
                    logger.warning(f"Failed to store embedding for chunk {item.get('chunk_id')}: {e}")
                    continue
            
            logger.info(f"Stored embeddings for {success_count}/{len(chunks_with_embeddings)} chunks")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            return False
    
    def similarity_search(self, query_embedding: List[float], file_id: str = None, 
                         limit: int = 10) -> List[Dict]:
        """Search for similar chunks using pgvector cosine similarity"""
        try:
            # Format query embedding for pgvector
            query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Build query with optional file filtering
            base_query = """
                SELECT 
                    c.chunk_id,
                    c.file_id,
                    c.content,
                    c.chunk_index,
                    c.chunk_metadata,
                    1 - (e.embedding <=> %s::vector) as similarity_score
                FROM chunks c
                JOIN embeddings e ON c.chunk_id = e.chunk_id
            """
            
            params = [query_embedding_str]
            
            if file_id:
                base_query += " WHERE c.file_id = %s"
                params.append(file_id)
            
            query = f"""
                {base_query}
                ORDER BY e.embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([query_embedding_str, limit])
            
            results = self.db.execute_query(query, tuple(params), fetch_results=True)
            
            similar_chunks = []
            for row in results:
                similar_chunks.append({
                    'chunk_id': str(row[0]),
                    'file_id': row[1],
                    'content': row[2],
                    'chunk_index': row[3],
                    'metadata': row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else {},
                    'similarity_score': float(row[5]) if row[5] else 0.0
                })
            
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    def get_embedding_stats(self, file_id: str) -> Dict:
        """Get embedding statistics for a document"""
        try:
            query = """
                SELECT 
                    COUNT(c.chunk_id) as total_chunks,
                    COUNT(e.chunk_id) as embedded_chunks,
                    e.model_name,
                    e.embedding_dim
                FROM chunks c
                LEFT JOIN embeddings e ON c.chunk_id = e.chunk_id
                WHERE c.file_id = %s
                GROUP BY e.model_name, e.embedding_dim
            """
            
            result = self.db.execute_query(query, (file_id,), fetch_results=True)
            
            if result:
                row = result[0]
                return {
                    'total_chunks': row[0],
                    'embedded_chunks': row[1],
                    'model_name': row[2],
                    'embedding_dim': row[3],
                    'embedding_coverage': (row[1] / row[0] * 100) if row[0] > 0 else 0
                }
            
            return {'total_chunks': 0, 'embedded_chunks': 0, 'embedding_coverage': 0}
            
        except Exception as e:
            logger.error(f"Error getting embedding stats for {file_id}: {e}")
            return {}


class DatabaseServices:
    """Main service container for your Flask app"""
    
    def __init__(self, db_manager):
        self.documents = DocumentService(db_manager)
        self.chunks = ChunkService(db_manager)
        self.embeddings = EmbeddingService(db_manager)
    
    def process_document(self, file_id: str, filename: str, source_type: str,
                        source_path: str, chunks: List[Dict], embeddings: List[List[float]],
                        file_size: int = None, public_url: str = None, 
                        metadata: dict = None) -> bool:
        """
        Complete document processing pipeline:
        1. Create document record
        2. Create chunks (for summarization)
        3. Store embeddings (for QA)
        """
        try:
            # Step 1: Create document
            if not self.documents.create_document(
                file_id, filename, source_type, source_path, 
                file_size, public_url, metadata
            ):
                return False
            
            # Step 2: Create chunks and get chunk_ids
            chunk_ids = self.chunks.create_chunks(file_id, chunks)
            if not chunk_ids:
                logger.error(f"Failed to create chunks for {file_id}")
                return False
            
            # Step 3: Store embeddings if provided
            if embeddings and len(embeddings) == len(chunk_ids):
                chunks_with_embeddings = [
                    {'chunk_id': chunk_id, 'embedding': embedding}
                    for chunk_id, embedding in zip(chunk_ids, embeddings)
                ]
                
                if not self.embeddings.store_embeddings(chunks_with_embeddings):
                    logger.warning(f"Failed to store some embeddings for {file_id}")
            
            logger.info(f"Successfully processed document {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {file_id}: {e}")
            # Cleanup on failure
            self.documents.delete_document(file_id)
            return False
    
    def delete_document_completely(self, file_id: str) -> bool:
        """
        Complete document deletion (cascades to chunks and embeddings)
        This satisfies your requirement for clean deletion
        """
        return self.documents.delete_document(file_id)