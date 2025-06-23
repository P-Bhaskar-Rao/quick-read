from flask import Flask, request, jsonify, session, make_response
from flask_session import Session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os, uuid

from utils import generate_enhanced_pdf
from summarizer import summarize_chunks
from crawler import crawl_site
from logger import setup_logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from embedding import embeddings
from supabase import create_client
from embed_pdf_to_pinecone import embed_pdf_to_pinecone
from prompt import *

load_dotenv()
logger = setup_logger("App")
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
Session(app)


CORS(app, 
     origins=["http://localhost:5173", "http://127.0.0.1:5173"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "Accept"],  
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Content-Disposition"])  

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
index_name = "quick-read-wizard"



@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current session status"""
    return jsonify({
        "file_info": session.get("file_info"),
        "summary": session.get("summary"),
        "answer": session.get("answer")
    })

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Upload PDF file"""
    if 'file' not in request.files:
        return jsonify({"error": "No file selected"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_bytes = file.read()

    try:
        # Upload to Supabase
        supabase.storage.from_("pdfs").upload(
            unique_filename, 
            file_bytes, 
            {"content-type": "application/pdf"}
        )
        public_url = supabase.storage.from_("pdfs").get_public_url(unique_filename)

        # Embed to Pinecone
        if public_url:
            embed_pdf_to_pinecone(supabase, "pdfs", unique_filename)

        #
        file_info = {
            "file_name": filename,
            "file_size": f"{len(file_bytes) / 1024 / 1024:.2f} MB",
            "file_id": unique_filename,
            "file_url": public_url,
            "content_type": "pdf"
        }
        session['file_info'] = file_info
        
        
        session.pop('summary', None)
        session.pop('answer', None)
        session.pop('suggested_questions', None)

        return jsonify({
            "success": True,
            "file_info": file_info,
            "message": "File uploaded successfully"
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route("/api/analyze-url", methods=["POST"])
def api_analyze_url():
    """Analyze URL content"""
    data = request.get_json()
    url = data.get("url")
    
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        content = crawl_site(url)
        if not content:
            return jsonify({"error": "Could not extract content from URL"}), 400

        # Update session
        file_info = {
            "file_name": f"Web: {url}",
            "file_size": "From URL",
            "file_id": None,
            "url_content": content,
            "content_type": "url",
            "original_url": url
        }
        session['file_info'] = file_info
 
        session.pop('summary', None)
        session.pop('answer', None)
        session.pop('suggested_questions', None)

        return jsonify({
            "success": True,
            "file_info": file_info,
            "message": "URL analyzed successfully"
        })

    except Exception as e:
        logger.error(f"URL analysis error: {e}")
        return jsonify({"error": f"URL analysis failed: {str(e)}"}), 500

@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    print("-"*80)
    file_info = session.get('file_info', {})
    if not file_info:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        if file_info.get('content_type') == 'url':
            content = file_info.get('url_content')
            if not content:
                summary = "No content found to summarize."
            else:
                summary = summarize_chunks(content)
                
        else:
            file_id = file_info.get('file_id')
            if not file_id:
                summary = "No file ID found."
            else:
                retriever = PineconeVectorStore.from_existing_index(
                    index_name=index_name,
                    embedding=embeddings
                ).as_retriever(
                    search_type='mmr',
                    search_kwargs={"k": 100, "filter": {"file_id": file_id}}
                )

                llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.5)

               
                prompt = ChatPromptTemplate.from_template(
                    summarize_prompt
                )

                rag_chain = create_retrieval_chain(
                    retriever,
                    create_stuff_documents_chain(llm, prompt)
                )

                response = rag_chain.invoke({"input": summarize_prompt})
                summary = response["answer"]
                
            print('summary:\n',summary)
            print("_"*80)
            session["summary"] = summary


        return jsonify({
            "success": True,
            "summary": summary
        })

    except Exception as e:
        logger.error(f"Summarization error: {e}")
        error_msg = f"Error generating summary: {str(e)}"
        session['summary'] = error_msg
        return jsonify({"error": error_msg}), 500

@app.route("/api/ask", methods=["POST"])
def api_ask():
    """Ask question about the document"""
    data = request.get_json()
    question = data.get("question")
    file_info = session.get("file_info", {})

    if not question:
        return jsonify({"error": "Please enter a question"}), 400

    if not file_info:
        return jsonify({"error": "Please upload a file first"}), 400

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
        prompt = ChatPromptTemplate.from_template(qa_prompt)

        if file_info.get('content_type') == 'pdf':
            file_id = file_info.get('file_id')
            if not file_id:
                answer = "No file ID found"
            else:
                retriever = PineconeVectorStore.from_existing_index(
                    index_name=index_name,
                    embedding=embeddings
                ).as_retriever(
                    search_type='similarity',
                    search_kwargs={"k": 3, "filter": {"file_id": file_id}}
                )

                rag_chain = create_retrieval_chain(
                    retriever,
                    create_stuff_documents_chain(llm, prompt)
                )

                response = rag_chain.invoke({"input": question})
                answer = response["answer"]

        elif file_info.get('content_type') == 'url':
            content = file_info.get('url_content', '')[:4000]
            if not content:
                answer = "No content available to answer questions"
            else:
                messages = prompt.format_messages(context=content, input=question)
                response = llm.invoke(messages)
                answer = response.content

        else:
            answer = "Unsupported content type"

        session['answer'] = answer
        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as e:
        logger.error(f"Question answering error: {e}")
        error_msg = f"Error answering question: {str(e)}"
        session['answer'] = error_msg
        return jsonify({"error": error_msg}), 500
    
    
@app.route("/api/clear-summary", methods=["POST"])
def api_clear_summary():
    """Clear summary"""
    session.pop('summary', None)
    return jsonify({"success": True})

@app.route("/api/remove", methods=["POST"])
def api_remove():
    """Remove uploaded file and clear session"""
    session.pop('file_info', None)
    session.pop('summary', None)
    session.pop('answer', None)
    session.pop('suggested_questions', None)
    return jsonify({"success": True})

@app.route("/api/download-summary", methods=["POST"])
def api_download_summary():
    """Download summary as well-formatted PDF"""
    summary = session.get("summary")
    file_info = session.get("file_info", {})
    
    if not summary:
        return jsonify({"error": "No summary available"}), 400

    try:
        filename = f"summary_{file_info.get('file_name', 'document').replace('/', '_')}.pdf"
        
        # Use enhanced PDF generation
        buffer = generate_enhanced_pdf(summary, title=f"Summary: {file_info.get('file_name', 'Document')}")
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = 'application/pdf'
        return response
    
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500
    
    
@app.route("/api/suggested-questions", methods=["POST"])
def api_suggested_questions():
    """Generate suggested questions for the document"""
    file_info = session.get('file_info', {})
    if not file_info:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
        prompt = ChatPromptTemplate.from_template(suggested_questions_prompt)

        if file_info.get('content_type') == 'pdf':
            file_id = file_info.get('file_id')
            if not file_id:
                return jsonify({"error": "No file ID found"}), 400
                
            # Get relevant content from Pinecone
            retriever = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings
            ).as_retriever(
                search_type='mmr',
                search_kwargs={"k": 20, "filter": {"file_id": file_id}}
            )
            
            
            docs = retriever.invoke("What is this document about? Summarize the main topics.")
            context = "\n\n".join([doc.page_content for doc in docs[:10]])  # Limit context
            
        elif file_info.get('content_type') == 'url':
            context = file_info.get('url_content', '')[:8000]  # Limit context for URL content
            if not context:
                return jsonify({"error": "No content available"}), 400
        else:
            return jsonify({"error": "Unsupported content type"}), 400

       
        messages = prompt.format_messages(context=context)
        response = llm.invoke(messages)
        
      
        questions_text = response.content.strip()
        questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
        
        
        cleaned_questions = []
        for q in questions:
            
            q = q.lstrip('0123456789.-• ').strip()
            if len(q) > 10 and q.endswith('?'):  # Valid question
                cleaned_questions.append(q)
        
        
        cleaned_questions = cleaned_questions[:4]
        print('cleaned questions: \n',cleaned_questions)
       
        if not cleaned_questions:
            cleaned_questions = [
                "What are the main points of this document?",
                "Can you explain the key findings?",
                "What are the conclusions?",
                "Are there any recommendations mentioned?",
            ]

        session['suggested_questions'] = cleaned_questions
        
        return jsonify({
            "success": True,
            "questions": cleaned_questions
        })

    except Exception as e:
        logger.error(f"Suggested questions error: {e}")
       
        default_questions = [
            "What are the main points of this document?",
            "Can you explain the key findings?",
            "What are the conclusions?",
        ]
        session['suggested_questions'] = default_questions
        return jsonify({
            "success": True,
            "questions": default_questions
        })

if __name__ == "__main__":
    PORT=os.getenv('PORT')
    app.run(host='127.0.0.1', debug=True, port=PORT)