from flask import Flask, request, jsonify, session, make_response
from flask_session import Session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os, uuid
import logging
from redis import Redis
from datetime import timedelta

from utils.pdf_utils import generate_enhanced_pdf
from summarizer import summarize_chunks
from crawler import crawl_site
from logger import setup_logger
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate

from config import AppConfig
from database_manager import DatabaseManager
from cloud_storage_pdf_loader import CloudStoragePDFLoader
from embed_pdf_to_cloudsql import (
    process_pdf_content,
    process_url_content,
    search_similar_content,
    delete_file_embeddings,
    create_tables_if_not_exists,
)
from decorators import (
    retry_on_rate_limit,
    require_file_upload,
    handle_exceptions,
    validate_request_data,
)
from embedding import vertex_ai_embeddings_instance
from utils.response_helpers import (
    validate_file_info,
    handle_api_error,
    get_content_for_processing,
)
from constants import *
from prompt import *
from google.cloud import storage

load_dotenv()
logger = setup_logger("App")

# === Configuration and Initialization ===

config = AppConfig()
config.validate_config()

db_manager = DatabaseManager(config)
storage_client = storage.Client(project=config.project_id)
pdf_loader = CloudStoragePDFLoader(storage_client, config.pdf_bucket_name)

llm = ChatVertexAI(
    model_name="gemini-1.5-flash",
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_REGION"),
)

try:
    create_tables_if_not_exists(db_manager)
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database tables: {e}")
    raise

app = Flask(__name__)
app.secret_key = config.app_secret_key

# === Redis Session Configuration ===

try:
    redis_client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=False,
        socket_timeout=5,
        socket_connect_timeout=5,
        health_check_interval=30,
    )
    redis_client.ping()
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis_client
    logger.info("Redis connection successful")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = "/tmp/flask_session"
    os.makedirs("/tmp/flask_session", exist_ok=True)
    logger.warning("Falling back to filesystem sessions")

app.config.update(
    SESSION_COOKIE_SECURE=True,  # Keep True for HTTPS deployment
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
)

Session(app)

# === CORS Configuration ===

CORS(
    app,
    origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://storage.googleapis.com",
        "https://quick-read-wizard.storage.googleapis.com",
    ],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "Accept"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["Content-Disposition"],
)


# Health check endpoint for Cloud Run
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({"status": "healthy", "service": "quick-read-wizard"}), 200


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current session status"""
    return jsonify(
        {
            "file_info": session.get("file_info"),
            "summary": session.get("summary"),
            "answer": session.get("answer"),
        }
    )


@app.route("/api/upload", methods=["POST"])
@handle_exceptions("Upload")
def api_upload():
    """Upload PDF file - ✅ Already follows correct architecture"""
    if "file" not in request.files:
        return jsonify({"error": "No file selected"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_bytes = file.read()

    try:
        # Upload to Google Cloud Storage
        bucket = storage_client.bucket(config.pdf_bucket_name)
        blob = bucket.blob(unique_filename)
        blob.upload_from_string(file_bytes, content_type="application/pdf", timeout=600)
        blob.make_public()
        public_url = blob.public_url

        # Store document metadata in Cloud SQL
        insert_doc_query = """
            INSERT INTO documents (file_id, original_filename, file_size, source_path, public_url, source_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_id) DO UPDATE SET
                original_filename = EXCLUDED.original_filename,
                file_size = EXCLUDED.file_size,
                source_path = EXCLUDED.source_path,
                public_url = EXCLUDED.public_url,
                source_type = EXCLUDED.source_type,
                updated_at = CURRENT_TIMESTAMP
        """

        db_manager.execute_query(
            insert_doc_query,
            (
                unique_filename,
                filename,
                len(file_bytes),
                unique_filename,
                public_url,
                "pdf",
            ),
        )

        # ✅ CORRECT: Process PDF and store both chunks AND embeddings
        embed_success = process_pdf_content(
            file_id=unique_filename,
            pdf_path=unique_filename,
            db_manager=db_manager,
            pdf_loader=pdf_loader,
            original_filename=filename,
        )

        if not embed_success:
            logger.warning(f"Failed to embed PDF {unique_filename}")

            # Clean up
            try:
                db_manager.execute_query(
                    "DELETE FROM documents WHERE file_id = %s", (unique_filename,)
                )
                bucket = storage_client.bucket(config.pdf_bucket_name)
                blob = bucket.blob(unique_filename)
                if blob.exists():
                    blob.delete()
                    logger.info(
                        f"Deleted blob {unique_filename} due to failed embedding"
                    )
            except Exception as cleanup_err:
                logger.warning(f"Cleanup after failed embedding failed: {cleanup_err}")

            return (
                jsonify(
                    {
                        "error": (
                            "This PDF could not be processed — it appears to be image-based or non-copyable. "
                            "We're working on adding OCR support soon. Try uploading another PDF with selectable text."
                        )
                    }
                ),
                400,
            )

        # Prepare file info for session
        file_info = {
            "file_name": filename,
            "file_size": f"{len(file_bytes) / 1024 / 1024:.2f} MB",
            "file_id": unique_filename,
            "file_url": public_url,
            "content_type": "pdf",
        }
        session["file_info"] = file_info

        # Clear previous session data
        session.pop("summary", None)
        session.pop("answer", None)
        session.pop("suggested_questions", None)

        return jsonify(
            {
                "success": True,
                "file_info": file_info,
                "message": "File uploaded successfully",
            }
        )

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route("/api/analyze-url", methods=["POST"])
@validate_request_data(["url"])
@handle_exceptions("URL Analysis")
def api_analyze_url():
    """
    ✅ UPDATED: Analyze URL content with correct unified architecture
    Now creates chunks and embeddings for URLs, not just session storage
    """
    data = request.get_json()
    url = data.get("url")

    try:
        result = crawl_site(url)

        if isinstance(result, tuple):
            result, _ = result

        content = result.get("text", "")
        if not content or not content.strip():
            return jsonify({"error": "Could not extract content from URL"}), 400

        # ✅ NEW: Generate unique file_id for URL content
        url_file_id = f"url_{uuid.uuid4().hex}"
        title = result.get("title", f"Web: {url}")

        # ✅ NEW: Process URL content using unified architecture
        # This creates chunks (for summarization) AND embeddings (for QA)
        embed_success = process_url_content(
            file_id=url_file_id,
            url=url,
            content=content,
            db_manager=db_manager,
            title=title,
        )

        if not embed_success:
            logger.warning(f"Failed to process URL content for {url}")
            return jsonify({"error": "Failed to process URL content"}), 500

        # ✅ UPDATED: Store file_id instead of raw content in session
        file_info = {
            "file_name": title,
            "file_size": "From URL",
            "file_id": url_file_id,
            "content_type": "url",
            "original_url": url,
        }
        session["file_info"] = file_info

        # Clear previous session data
        session.pop("summary", None)
        session.pop("answer", None)
        session.pop("suggested_questions", None)

        return jsonify(
            {
                "success": True,
                "file_info": file_info,
                "message": "URL analyzed successfully",
            }
        )

    except Exception as e:
        logger.error(f"URL analysis error: {e}")
        return jsonify({"error": f"URL analysis failed: {str(e)}"}), 500


@retry_on_rate_limit(max_retries=3)
def safe_llm_invoke(messages):
    return llm.invoke(messages)


@app.route("/api/summarize", methods=["POST"])
@require_file_upload
@handle_exceptions("Summarization")
def api_summarize():
    """
    ✅ PERFECT: Generate summary using RAW TEXT CHUNKS for both PDF and URL
    This is the correct architecture - no embeddings used for summarization
    """
    print("-" * 80)
    file_info = session.get("file_info", {})

    try:
        file_id = file_info.get("file_id")
        if not file_id:
            return jsonify({"error": "No file ID found"}), 400

        # ✅ UNIFIED: Both PDF and URL now use the same approach
        # Get RAW TEXT CHUNKS from database (not embeddings)
        from embed_pdf_to_cloudsql import get_content_for_summary

        chunks_data = get_content_for_summary(file_id, db_manager)

        if not chunks_data:
            summary = "No content available for summarization."
        else:
            # ✅ UNIFIED: Use same summarizer for both content types
            from summarizer import summarize_pdf_content_from_chunks

            summary = summarize_pdf_content_from_chunks(chunks_data)

        print("summary:\n", summary)
        print("_" * 80)
        session["summary"] = summary

        return jsonify({"success": True, "summary": summary})

    except Exception as e:
        logger.error(f"Summarization error: {e}")
        error_msg = f"Error generating summary: {str(e)}"
        session["summary"] = error_msg
        return jsonify({"error": error_msg}), 500


@app.route("/api/ask", methods=["POST"])
@require_file_upload
@validate_request_data(["question"])
@handle_exceptions("Question Answering")
def api_ask():
    """
    ✅ PERFECT: QA using embeddings for both PDF and URL
    This is the correct architecture - uses vector similarity search
    """
    data = request.get_json()
    question = data.get("question")
    file_info = session.get("file_info", {})

    try:
        llm.temperature = DEFAULT_TEMPERATURE_QA
        prompt = ChatPromptTemplate.from_template(qa_prompt)

        file_id = file_info.get("file_id")
        if not file_id:
            return jsonify({"error": "No file ID found"}), 400

        # ✅ UNIFIED: Both PDF and URL use same embedding-based search
        relevant_docs = search_similar_content(
            query=question,
            file_id=file_id,
            limit=DEFAULT_SIMILARITY_LIMIT,
            db_manager=db_manager,
        )

        if not relevant_docs:
            answer = "No relevant content found to answer your question."
        else:
            context = "\n\n".join([doc["content"] for doc in relevant_docs])
            messages = prompt.format_messages(context=context, input=question)
            response = safe_llm_invoke(messages)
            answer = response.content

        session["answer"] = answer
        return jsonify({"success": True, "answer": answer})

    except Exception as e:
        logger.error(f"Question answering error: {e}")
        error_msg = f"Error answering question: {str(e)}"
        session["answer"] = error_msg
        return jsonify({"error": error_msg}), 500


@app.route("/api/clear-summary", methods=["POST"])
def api_clear_summary():
    """Clear summary"""
    session.pop("summary", None)
    return jsonify({"success": True})


@app.route("/api/remove", methods=["POST"])
@handle_exceptions("File Removal")
def api_remove():
    """
    ✅ UPDATED: Remove uploaded file and clear session for both PDF and URL
    Now handles URL cleanup from database as well
    """
    file_info = session.get("file_info", {})

    if file_info:
        file_id = file_info.get("file_id")
        content_type = file_info.get("content_type")

        if file_id:
            try:
                # ✅ UNIFIED: Delete embeddings and chunks for both PDF and URL
                delete_file_embeddings(file_id, db_manager)

                # ✅ UPDATED: Handle Cloud Storage cleanup only for PDFs
                if content_type == "pdf":
                    try:
                        bucket = storage_client.bucket(config.pdf_bucket_name)
                        blob = bucket.blob(file_id)
                        if blob.exists():
                            blob.delete()
                            logger.info(f"Deleted blob {file_id} from Cloud Storage")
                    except Exception as e:
                        logger.warning(f"Failed to delete blob from Cloud Storage: {e}")

                logger.info(f"Successfully cleaned up {content_type} file: {file_id}")

            except Exception as e:
                logger.error(f"Error cleaning up file {file_id}: {e}")

    # Clear session data
    session.pop("file_info", None)
    session.pop("summary", None)
    session.pop("answer", None)
    session.pop("suggested_questions", None)

    return jsonify({"success": True})


@app.route("/api/download-summary", methods=["POST"])
@handle_exceptions("PDF Generation")
def api_download_summary():
    """Download summary as well-formatted PDF"""
    summary = session.get("summary")
    file_info = session.get("file_info", {})

    if not summary:
        return jsonify({"error": "No summary available"}), 400

    try:
        filename = (
            f"summary_{file_info.get('file_name', 'document').replace('/', '_')}.pdf"
        )

        buffer = generate_enhanced_pdf(
            summary, title=f"Summary: {file_info.get('file_name', 'Document')}"
        )

        response = make_response(buffer.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = "application/pdf"
        return response

    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


@app.route("/api/suggested-questions", methods=["POST"])
@require_file_upload
@handle_exceptions("Suggested Questions Generation")
def api_suggested_questions():
    """
    ✅ UPDATED: Generate suggested questions using embeddings for both PDF and URL
    Uses vector similarity search to get relevant context
    """
    file_info = session.get("file_info", {})

    try:
        llm.temperature = DEFAULT_TEMPERATURE_SUGGESTIONS
        prompt = ChatPromptTemplate.from_template(suggested_questions_prompt)

        file_id = file_info.get("file_id")
        if not file_id:
            return jsonify({"error": "No file ID found"}), 400

        # ✅ UNIFIED: Both PDF and URL use same embedding-based approach
        relevant_docs = search_similar_content(
            query="What is this document about? Summarize the main topics.",
            file_id=file_id,
            limit=20,
            db_manager=db_manager,
        )

        context = (
            "\n\n".join([doc["content"] for doc in relevant_docs[:10]])
            if relevant_docs
            else "No content available"
        )

        if not context or context == "No content available":
            return jsonify({"error": "No content available"}), 400

        messages = prompt.format_messages(context=context)
        response = safe_llm_invoke(messages)
        questions_text = response.content.strip()
        questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

        cleaned_questions = []
        for q in questions:
            q = q.lstrip("0123456789.-• ").strip()
            if len(q) > 10 and q.endswith("?"):
                cleaned_questions.append(q)

        cleaned_questions = cleaned_questions[:4] or DEFAULT_QUESTIONS
        session["suggested_questions"] = cleaned_questions
        return jsonify({"success": True, "questions": cleaned_questions})

    except Exception as e:
        logger.error(f"Suggested questions error: {e}")
        session["suggested_questions"] = DEFAULT_QUESTIONS[:3]
        return jsonify({"success": True, "questions": DEFAULT_QUESTIONS[:3]})


@app.route("/api/debug-session")
def debug_session():
    return jsonify({
        "file_info": session.get("file_info"),
        "summary": session.get("summary"),
        "keys": list(session.keys())
    })

if __name__ == "__main__":

    PORT = int(os.getenv("PORT", 8080))

    app.run(host="0.0.0.0", port=int(PORT), debug=False)
