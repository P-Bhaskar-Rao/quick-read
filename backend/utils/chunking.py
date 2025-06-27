from langchain.text_splitter import RecursiveCharacterTextSplitter

def split_into_chunks(text: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)
