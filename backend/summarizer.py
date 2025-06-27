import os
import vertexai
from vertexai.generative_models import GenerativeModel
from prompt import *
from dotenv import load_dotenv
import logging
from typing import List, Dict, Union
from utils.exceptions import GeminiRateLimitError, GeminiAPIError
import time
from decorators import retry_on_rate_limit

logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

if not PROJECT_ID or not REGION:
    logger.error("GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_REGION not set for Vertex AI (summarizer) initialization.")
    raise ValueError("Missing GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_REGION environment variables.")

try:
    vertexai.init(project=PROJECT_ID, location=REGION)
    logger.info("Vertex AI initialized successfully in summarizer")
except Exception as e:
    logger.warning(f"Vertex AI already initialized or initialization failed in summarizer: {e}")

# Initialize Gemini model
gemini_model = GenerativeModel("gemini-1.5-flash")
logger.info('Vertex AI Gemini model (gemini-1.5-flash) initialized.')

@retry_on_rate_limit(max_retries=3, base_delay=5)
def get_gemini_response(prompt: str, temperature: float = 0.3) -> str:
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": 8192,
            }
        )
        if not hasattr(response, "text") or not response.text.strip():
            raise GeminiAPIError("Received empty response from Gemini.")
        return response.text

    except Exception as e:
        error_str = str(e).lower()
        if "resource exhausted" in error_str or "429" in error_str:
            raise GeminiRateLimitError("Gemini rate limit exceeded.") from e
        elif "invalid argument" in error_str:
            raise GeminiAPIError("Invalid input to Gemini.") from e
        elif "unauthorized" in error_str:
            raise GeminiAPIError("Unauthorized access to Gemini.") from e
        else:
            raise GeminiAPIError(f"Unexpected Gemini error: {e}") from e

def summarize_chunks(content: Union[str, List[str]]) -> str:
    summary_blocks = []

    if isinstance(content, str):
        chunks = [content]
    elif isinstance(content, list) and content:
        chunks = content
    else:
        return "No content provided for summarization."

    max_chunk_size = 6000

    for i, chunk in enumerate(chunks):
        chunk_to_process = chunk[:max_chunk_size]
        prompt = f"{summarize_prompt}\n\nContent:\n{chunk_to_process}"
        summary = None

        for retry in range(3):
            try:
                summary = get_gemini_response(prompt, temperature=0.3)
                break
            except GeminiRateLimitError:
                logger.warning(f"Retrying chunk {i+1} due to Gemini rate limit ({retry+1}/3)...")
                time.sleep(5 * (retry + 1))
            except GeminiAPIError as e:
                logger.error(f"Gemini error summarizing section {i+1}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error summarizing section {i+1}: {e}")
                break
        else:
            logger.warning(f"Skipping section {i+1} after all retries failed.")
            continue

        if summary:
            summary_blocks.append(summary)

        time.sleep(1.5)

    full_summary = "\n\n---\n\n".join(summary_blocks)
    
    if not full_summary:
        return "Summary could not be generated due to API limits. Please try again later."

    # Re-chunk full_summary if it's too large (>8000 chars)
    if len(full_summary) > 8000:
        safe_chunks = [full_summary[i:i + 4000] for i in range(0, len(full_summary), 4000)]
        prompt = f"{summarize_prompt}\n\nContent:\n" + "\n\n".join(safe_chunks[:2])
    else:
        prompt = f"{summarize_prompt}\n\nContent:\n{full_summary}"

    try:
        brief_summary = get_gemini_response(prompt, temperature=0.2)
        return brief_summary
    except Exception as e:
        logger.error(f"Error generating brief summary: {e}")
        return full_summary  # fallback to full if brief fails

def summarize_pdf_content_from_chunks(chunks_data: List[Dict]) -> str:
    if not chunks_data:
        return "No content available to summarize."

    raw_text_chunks = []
    for chunk in chunks_data:
        if isinstance(chunk, dict) and 'content' in chunk:
            raw_text_chunks.append(chunk['content'])
        elif isinstance(chunk, str):
            raw_text_chunks.append(chunk)

    if not raw_text_chunks:
        return "No valid content found in chunks."

    max_chunks_for_summary = 15
    limited_chunks = raw_text_chunks[:max_chunks_for_summary]
    logger.info(f"Summarizing {len(limited_chunks)} chunks from PDF")

    return summarize_chunks(limited_chunks)

def summarize_url_content(url_content: str) -> str:
    if not url_content or not url_content.strip():
        return "No content available to summarize from URL."

    from langchain.text_splitter import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=200
    )

    chunks = text_splitter.split_text(url_content)
    logger.info(f"Summarizing URL content split into {len(chunks)} chunks")

    return summarize_chunks(chunks)

def summarize_pdf_content(content_list: list, max_sections: int = 10) -> str:
    logger.warning("Using legacy summarize_pdf_content function. Consider using summarize_pdf_content_from_chunks.")

    if not content_list:
        return "No content available to summarize."

    limited_content = content_list[:max_sections]
    return summarize_chunks(limited_content)
