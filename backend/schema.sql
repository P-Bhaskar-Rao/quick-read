-- Simplified Database Schema for RAG Application
-- Focused on core functionality: documents, chunks, and embeddings
-- No analytics, no cached summaries - clean deletion when user removes content

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. DOCUMENTS TABLE
-- Stores metadata about uploaded files and URLs
CREATE TABLE IF NOT EXISTS documents (
    file_id VARCHAR(255) PRIMARY KEY,  -- UUID-based filename for PDFs, or hash for URLs
    original_filename VARCHAR(500),     -- Original PDF name or URL title
    source_type VARCHAR(10) NOT NULL CHECK (source_type IN ('pdf', 'url')),
    source_path TEXT,                  -- GCS path for PDFs, original URL for web content
    file_size BIGINT,                  -- File size in bytes (NULL for URLs)
    public_url TEXT,                   -- Public access URL (for PDFs in GCS)
    content_hash VARCHAR(64),          -- SHA-256 hash to detect duplicates
    metadata JSONB,                    -- Additional metadata (PDF pages, URL domain, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. CHUNKS TABLE
-- Stores raw text chunks extracted from documents (used for both QA and summarization)
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id VARCHAR(255) NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,      -- Order of chunk within document (0, 1, 2...)
    content TEXT NOT NULL,             -- Raw text content of the chunk
    chunk_metadata JSONB,              -- Page number, section, token count, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique ordering per file
    UNIQUE(file_id, chunk_index)
);

-- 3. EMBEDDINGS TABLE
-- Stores vector embeddings for semantic search (QA functionality)
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    embedding VECTOR(768),             -- pgvector for efficient vector operations
    model_name VARCHAR(100) DEFAULT 'textembedding-gecko',
    embedding_dim INTEGER DEFAULT 768,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES for Performance
-- Core lookup indexes
CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file_id_index ON chunks(file_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Vector similarity search index (pgvector)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Content search indexes for text-based search
CREATE INDEX IF NOT EXISTS idx_chunks_content_search ON chunks 
    USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_documents_filename_search ON documents 
    USING gin(to_tsvector('english', original_filename));

-- TRIGGERS for auto-updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- UTILITY VIEWS
-- View for document statistics (useful for debugging)
CREATE OR REPLACE VIEW document_stats AS
SELECT 
    d.file_id,
    d.original_filename,
    d.source_type,
    COUNT(c.chunk_id) as chunk_count,
    COUNT(e.chunk_id) as embedded_chunks,
    d.file_size,
    d.created_at
FROM documents d
LEFT JOIN chunks c ON d.file_id = c.file_id
LEFT JOIN embeddings e ON c.chunk_id = e.chunk_id
GROUP BY d.file_id, d.original_filename, d.source_type, d.file_size, d.created_at
ORDER BY d.created_at DESC;

-- View for checking embedding coverage
CREATE OR REPLACE VIEW embedding_coverage AS
SELECT 
    d.file_id,
    d.original_filename,
    COUNT(c.chunk_id) as total_chunks,
    COUNT(e.chunk_id) as embedded_chunks,
    CASE 
        WHEN COUNT(c.chunk_id) = 0 THEN 0
        ELSE ROUND((COUNT(e.chunk_id)::DECIMAL / COUNT(c.chunk_id) * 100), 2)
    END as embedding_percentage
FROM documents d
LEFT JOIN chunks c ON d.file_id = c.file_id
LEFT JOIN embeddings e ON c.chunk_id = e.chunk_id
GROUP BY d.file_id, d.original_filename
ORDER BY embedding_percentage DESC;