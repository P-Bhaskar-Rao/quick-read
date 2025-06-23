from supabase import Client
import tempfile, os, logging
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)

class SupabasePDFLoader:
    def __init__(self, supabase_client: Client, bucket: str = "pdfs"):
        self.supabase = supabase_client
        self.bucket = bucket
        logger.info("SupabasePDFLoader initialized with external client")

    def load(self, filename: str):
        try:
            logger.info(f"Downloading {filename} from bucket: {self.bucket}")
            pdf_bytes = self.supabase.storage.from_(self.bucket).download(filename)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                temp_path = tmp.name

            logger.info(f"Saved temp file: {temp_path}")

            loader = PyPDFLoader(temp_path)
            documents = loader.load()

            logger.info(f"Loaded {len(documents)} pages from {filename}")
            return documents

        except Exception as e:
            logger.error(f"Failed to load: {e}", exc_info=True)
            raise

        finally:
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"Temp file deleted: {temp_path}")
            except Exception as cleanup_err:
                logger.warning(f"Cleanup error: {cleanup_err}")
