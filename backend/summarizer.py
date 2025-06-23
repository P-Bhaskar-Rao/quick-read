import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from prompt import *
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')

gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3
)

prompt = ChatPromptTemplate.from_template(url_summarize_prompt)

parser = StrOutputParser()
chain = prompt | gemini | parser

def summarize_chunks(chunks):
    summary_blocks = []
    for i, chunk in enumerate(chunks):
        try:
            # Get the markdown summary from the LLM
            summary = chain.invoke({"content": chunk})
            # Add a section header in markdown format
            summary_blocks.append(f"# Section {i+1}\n\n{summary}")
        except Exception as e:
            summary_blocks.append(f"## Section {i+1} - Error\n\n*Failed to summarize section {i+1}: {e}*")
    return "\n\n---\n\n".join(summary_blocks)