# pdf_to_pinecone.py

from data_extraction import text_split
from embedding import embeddings
from pinecone.grpc import PineconeGRPC as Pinecone
from langchain_pinecone import PineconeVectorStore
from pinecone import ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
import tempfile, os, logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def embed_pdf_to_pinecone(supabase_client, bucket_name: str, filename: str, index_name = 'quick-read-wizard'):
    temp_path=None
    try:
        PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
        pc = Pinecone(api_key=PINECONE_API_KEY)

        # Create index if not exists
        if not pc.has_index(index_name):
            pc.create_index(
                name=index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

        # 🔽 Step 1: Download PDF from Supabase
        logger.info(f"Downloading '{filename}' from Supabase bucket '{bucket_name}'")
        file_bytes = supabase_client.storage.from_(bucket_name).download(filename)

        # 🔽 Step 2: Save as temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name

        # 🔽 Step 3: Load and chunk the document
        loader = PyPDFLoader(temp_path)
        documents = loader.load()
        chunks = text_split(documents)
        
        # 🔽 Step 4: Wrap chunks with metadata
        file_id = filename  
        documents_with_metadata = [
            Document(page_content=chunk.page_content, metadata={"file_id": file_id})
            for chunk in chunks
        ]

        # 🔽 Step 5: Embed and store in Pinecone
        PineconeVectorStore.from_documents(
            documents=documents_with_metadata,
            index_name=index_name,
            embedding=embeddings
        )

        logger.info(f"Embedded {len(chunks)} chunks from '{filename}' into Pinecone index '{index_name}' with metadata")

    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        raise

    finally:
        # Cleanup temp file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Deleted temp file: {temp_path}")
        except Exception as cleanup_err:
            logger.warning(f"Temp file deletion error: {cleanup_err}")
