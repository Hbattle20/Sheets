-- Create table for document chunks with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT '10-K',
    filing_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    section TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(3072) NOT NULL,  -- OpenAI text-embedding-3-large
    word_count INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_document_chunks_company_id ON document_chunks(company_id);
CREATE INDEX idx_document_chunks_ticker ON document_chunks(ticker);
CREATE INDEX idx_document_chunks_filing_date ON document_chunks(filing_date);
CREATE INDEX idx_document_chunks_section ON document_chunks(section);
CREATE INDEX idx_document_chunks_fiscal_year ON document_chunks(fiscal_year);

-- Note: pgvector indexes (ivfflat and hnsw) support max 2000 dimensions
-- Since we're using 3072-dimensional embeddings, we'll skip the index for now
-- Similarity search will still work, just slightly slower for large datasets
-- For production with millions of vectors, consider:
-- 1. Using text-embedding-3-small (1536 dimensions) instead
-- 2. Dimension reduction (PCA, UMAP) to reduce to <2000 dimensions
-- 3. Using a dedicated vector database like Pinecone or Weaviate

-- Function to search for similar chunks
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(3072),
    match_count INT DEFAULT 5,
    filter_ticker TEXT DEFAULT NULL,
    filter_year INT DEFAULT NULL,
    filter_section TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id TEXT,
    ticker TEXT,
    filing_date DATE,
    section TEXT,
    text TEXT,
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.chunk_id,
        dc.ticker,
        dc.filing_date,
        dc.section,
        dc.text,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        dc.metadata
    FROM document_chunks dc
    WHERE 
        (filter_ticker IS NULL OR dc.ticker = filter_ticker)
        AND (filter_year IS NULL OR dc.fiscal_year = filter_year)
        AND (filter_section IS NULL OR dc.section = filter_section)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to get chunks for a specific company and year
CREATE OR REPLACE FUNCTION get_document_chunks(
    p_ticker TEXT,
    p_year INT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id TEXT,
    section TEXT,
    chunk_index INT,
    text TEXT,
    word_count INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.chunk_id,
        dc.section,
        dc.chunk_index,
        dc.text,
        dc.word_count
    FROM document_chunks dc
    WHERE 
        dc.ticker = p_ticker
        AND (p_year IS NULL OR dc.fiscal_year = p_year)
    ORDER BY dc.fiscal_year DESC, dc.chunk_index;
END;
$$;

-- Add update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_document_chunks_updated_at 
BEFORE UPDATE ON document_chunks 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();