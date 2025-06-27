"""
Replacement for supabase_pdf_loader.py
Handles PDF loading from Google Cloud Storage instead of Supabase
"""

import os
import tempfile
import logging
from typing import List, Optional
from google.cloud import storage
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document

logger = logging.getLogger(__name__)

class CloudStoragePDFLoader:
    """
    PDF loader for Google Cloud Storage
    Replaces SupabasePDFLoader functionality
    """
    
    def __init__(self, storage_client: Optional[storage.Client] = None, bucket_name: str = "pdfs"):
        """
        Initialize the Cloud Storage PDF loader
        
        Args:
            storage_client: Google Cloud Storage client (optional, will create if None)
            bucket_name: Name of the storage bucket containing PDFs
        """
        self.storage_client = storage_client or storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        logger.info(f"CloudStoragePDFLoader initialized for bucket: {bucket_name}")

    def load(self, blob_name: str) -> List[Document]:
        """
        Load a PDF from Cloud Storage and return LangChain documents
        
        Args:
            blob_name: Name of the PDF blob in the storage bucket
            
        Returns:
            List of LangChain Document objects
            
        Raises:
            Exception: If PDF loading fails
        """
        temp_path = None
        try:
            logger.info(f"Loading PDF: {blob_name} from bucket: {self.bucket_name}")
            
            # Get the blob
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                raise FileNotFoundError(f"Blob {blob_name} does not exist in bucket {self.bucket_name}")
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                blob.download_to_file(tmp)
                temp_path = tmp.name
            
            logger.info(f"Downloaded PDF to temporary file: {temp_path}")
            
            # Load PDF using LangChain PyPDFLoader
            loader = PyPDFLoader(temp_path)
            documents = loader.load()
            
            # Add Cloud Storage metadata to each document
            for doc in documents:
                doc.metadata.update({
                    'source_bucket': self.bucket_name,
                    'source_blob': blob_name,
                    'storage_type': 'google_cloud_storage'
                })
            
            logger.info(f"Successfully loaded {len(documents)} pages from {blob_name}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load PDF {blob_name}: {e}", exc_info=True)
            raise
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up temporary file: {cleanup_err}")

    def load_and_split(self, blob_name: str, text_splitter=None) -> List[Document]:
        """
        Load a PDF and split it into chunks
        
        Args:
            blob_name: Name of the PDF blob in the storage bucket
            text_splitter: Text splitter to use (optional)
            
        Returns:
            List of split Document objects
        """
        documents = self.load(blob_name)
        
        if text_splitter:
            return text_splitter.split_documents(documents)
        else:
            # Use default splitting from data_extraction if available
            try:
                from data_extraction import text_split
                return text_split(documents)
            except ImportError:
                logger.warning("data_extraction.text_split not available, returning unsplit documents")
                return documents

    def list_pdfs(self) -> List[str]:
        """
        List all PDF files in the bucket
        
        Returns:
            List of PDF blob names
        """
        try:
            pdf_blobs = []
            for blob in self.bucket.list_blobs():
                if blob.name.lower().endswith('.pdf'):
                    pdf_blobs.append(blob.name)
            
            logger.info(f"Found {len(pdf_blobs)} PDF files in bucket {self.bucket_name}")
            return pdf_blobs
            
        except Exception as e:
            logger.error(f"Failed to list PDFs in bucket {self.bucket_name}: {e}")
            return []

    def get_pdf_info(self, blob_name: str) -> dict:
        """
        Get information about a PDF blob
        
        Args:
            blob_name: Name of the PDF blob
            
        Returns:
            Dictionary with blob information
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()  # Fetch current blob properties
            
            return {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated,
                'md5_hash': blob.md5_hash,
                'public_url': blob.public_url if blob.public_url_set else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get info for PDF {blob_name}: {e}")
            return {}

    def delete_pdf(self, blob_name: str) -> bool:
        """
        Delete a PDF from Cloud Storage
        
        Args:
            blob_name: Name of the PDF blob to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Deleted PDF: {blob_name} from bucket: {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete PDF {blob_name}: {e}")
            return False

    def upload_pdf(self, local_path: str, blob_name: str, make_public: bool = False) -> bool:
        """
        Upload a PDF to Cloud Storage
        
        Args:
            local_path: Path to local PDF file
            blob_name: Name for the blob in storage
            make_public: Whether to make the blob publicly accessible
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            blob = self.bucket.blob(blob_name)
            
            with open(local_path, 'rb') as pdf_file:
                blob.upload_from_file(pdf_file, content_type='application/pdf')
            
            if make_public:
                blob.make_public()
                logger.info(f"Made blob {blob_name} publicly accessible")
            
            logger.info(f"Uploaded PDF: {local_path} as {blob_name} to bucket: {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload PDF {local_path}: {e}")
            return False


# Backward compatibility class name
class SupabasePDFLoader(CloudStoragePDFLoader):
    """
    Deprecated: Use CloudStoragePDFLoader instead
    This class is kept for backward compatibility
    """
    
    def __init__(self, supabase_client=None, bucket: str = "pdfs"):
        logger.warning("SupabasePDFLoader is deprecated. Use CloudStoragePDFLoader instead.")
        # Initialize with Cloud Storage instead
        super().__init__(bucket_name=bucket)


# Convenience function for quick loading
def load_pdf_from_storage(bucket_name: str, blob_name: str, 
                         storage_client: Optional[storage.Client] = None) -> List[Document]:
    """
    Convenience function to load a PDF directly from Cloud Storage
    
    Args:
        bucket_name: Name of the storage bucket
        blob_name: Name of the PDF blob
        storage_client: Google Cloud Storage client (optional)
        
    Returns:
        List of LangChain Document objects
    """
    loader = CloudStoragePDFLoader(storage_client, bucket_name)
    return loader.load(blob_name)