from langchain.text_splitter import RecursiveCharacterTextSplitter

def text_split(extracted_data):
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=30)
    text_chunks=text_splitter.split_documents(extracted_data)
    return text_chunks



