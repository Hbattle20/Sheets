#!/usr/bin/env python3
"""
Load document embeddings from Parquet files into Supabase with pgvector
"""

import os
import sys
import glob
import logging
from datetime import datetime
import pandas as pd
import pyarrow.parquet as pq
import psycopg2
from psycopg2.extras import execute_batch, Json
from tqdm import tqdm
from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmbeddingLoader:
    """Load embeddings into Supabase with pgvector"""
    
    def __init__(self):
        """Initialize database connection"""
        # Get database URL from environment
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Parse ticker to company_id mapping (we'll need to get this from DB)
        self.company_id_map = {}
        
    def get_connection(self):
        """Create a database connection"""
        return psycopg2.connect(self.database_url)
    
    def setup_pgvector(self):
        """Ensure pgvector extension is enabled"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if extension exists
                    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    if not cur.fetchone():
                        logger.info("Creating pgvector extension...")
                        cur.execute("CREATE EXTENSION vector")
                        conn.commit()
                    else:
                        logger.info("pgvector extension already enabled")
        except Exception as e:
            logger.error(f"Error setting up pgvector: {e}")
            raise
    
    def create_tables(self):
        """Create the document_chunks table if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Read and execute the SQL file
                    with open('create_vector_tables.sql', 'r') as f:
                        sql = f.read()
                    cur.execute(sql)
                    conn.commit()
                    logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def get_company_id(self, ticker: str) -> int:
        """Get company_id for a ticker"""
        if ticker in self.company_id_map:
            return self.company_id_map[ticker]
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
                    result = cur.fetchone()
                    if result:
                        self.company_id_map[ticker] = result[0]
                        return result[0]
                    else:
                        # Create company if it doesn't exist
                        cur.execute("""
                            INSERT INTO companies (ticker, name) 
                            VALUES (%s, %s) 
                            RETURNING id
                        """, (ticker, f"{ticker} Inc."))
                        company_id = cur.fetchone()[0]
                        conn.commit()
                        self.company_id_map[ticker] = company_id
                        logger.info(f"Created company record for {ticker} with id {company_id}")
                        return company_id
        except Exception as e:
            logger.error(f"Error getting company_id for {ticker}: {e}")
            raise
    
    def load_parquet_file(self, parquet_path: str) -> int:
        """Load a single Parquet file into the database"""
        logger.info(f"\nLoading: {parquet_path}")
        
        try:
            # Read Parquet file
            df = pd.read_parquet(parquet_path)
            logger.info(f"  Loaded {len(df)} chunks from Parquet")
            
            # Get ticker and company_id
            ticker = df['ticker'].iloc[0]
            company_id = self.get_company_id(ticker)
            
            # Prepare data for insertion
            records = []
            for _, row in df.iterrows():
                # Extract year from filing_date
                filing_date = row['filing_date']
                fiscal_year = int(filing_date[:4])
                
                # Convert embedding to list if it's numpy array
                embedding = row['embedding']
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                
                # Prepare metadata
                metadata = {
                    'chunk_index': row['chunk_index'],
                    'word_count': row['word_count'],
                    'original_file': os.path.basename(parquet_path)
                }
                
                record = (
                    row['chunk_id'],
                    company_id,
                    ticker,
                    '10-K',
                    filing_date,
                    fiscal_year,
                    row['section'],
                    row['chunk_index'],
                    len(df),  # total_chunks
                    row['text'],
                    embedding,
                    row['word_count'],
                    Json(metadata)
                )
                records.append(record)
            
            # Insert records in batches
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if chunks already exist
                    cur.execute("""
                        SELECT COUNT(*) FROM document_chunks 
                        WHERE ticker = %s AND filing_date = %s
                    """, (ticker, filing_date))
                    existing_count = cur.fetchone()[0]
                    
                    if existing_count > 0:
                        logger.warning(f"  Found {existing_count} existing chunks for {ticker} {filing_date}")
                        response = input("  Replace existing chunks? (yes/no): ")
                        if response.lower() != 'yes':
                            logger.info("  Skipping file")
                            return 0
                        
                        # Delete existing chunks
                        cur.execute("""
                            DELETE FROM document_chunks 
                            WHERE ticker = %s AND filing_date = %s
                        """, (ticker, filing_date))
                        logger.info(f"  Deleted {existing_count} existing chunks")
                    
                    # Insert new chunks
                    insert_query = """
                        INSERT INTO document_chunks (
                            chunk_id, company_id, ticker, document_type, filing_date,
                            fiscal_year, section, chunk_index, total_chunks, text,
                            embedding, word_count, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    # Use execute_batch for better performance
                    execute_batch(cur, insert_query, records, page_size=100)
                    conn.commit()
                    
                    logger.info(f"  ✓ Inserted {len(records)} chunks successfully")
                    return len(records)
                    
        except Exception as e:
            logger.error(f"Error loading {parquet_path}: {e}")
            raise
    
    def load_all_embeddings(self, pattern: str = "output/MSFT_*/*_embedded.parquet"):
        """Load all embedding files matching the pattern"""
        # Find all Parquet files
        parquet_files = glob.glob(pattern)
        parquet_files.sort()  # Sort by year
        
        if not parquet_files:
            logger.error(f"No files found matching pattern: {pattern}")
            return
        
        logger.info(f"Found {len(parquet_files)} Parquet files to load")
        
        # Ensure pgvector is set up
        self.setup_pgvector()
        
        # Create tables if needed
        logger.info("\nCreating tables if they don't exist...")
        self.create_tables()
        
        # Load each file
        total_chunks = 0
        successful_files = 0
        
        for parquet_file in parquet_files:
            try:
                chunks_loaded = self.load_parquet_file(parquet_file)
                if chunks_loaded > 0:
                    total_chunks += chunks_loaded
                    successful_files += 1
            except Exception as e:
                logger.error(f"Failed to load {parquet_file}: {e}")
                continue
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("LOADING COMPLETE")
        logger.info("="*60)
        logger.info(f"Files processed: {successful_files}/{len(parquet_files)}")
        logger.info(f"Total chunks loaded: {total_chunks}")
        
        # Test the search function
        if total_chunks > 0:
            self.test_search()
    
    def test_search(self):
        """Test the vector search functionality"""
        logger.info("\nTesting vector search...")
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get a random embedding to use as query
                    cur.execute("""
                        SELECT embedding, text, section 
                        FROM document_chunks 
                        WHERE section LIKE '%Risk%' 
                        LIMIT 1
                    """)
                    result = cur.fetchone()
                    
                    if result:
                        query_embedding = result[0]
                        query_text = result[1][:100] + "..."
                        query_section = result[2]
                        
                        logger.info(f"\nQuery text: {query_text}")
                        logger.info(f"Query section: {query_section}")
                        
                        # Search for similar chunks
                        cur.execute("""
                            SELECT 
                                chunk_id,
                                ticker,
                                filing_date,
                                section,
                                1 - (embedding <=> %s) AS similarity,
                                text
                            FROM document_chunks
                            WHERE chunk_id != %s
                            ORDER BY embedding <=> %s
                            LIMIT 5
                        """, (query_embedding, result[1], query_embedding))
                        
                        logger.info("\nTop 5 similar chunks:")
                        for row in cur.fetchall():
                            logger.info(f"  - {row[1]} {row[2]} | {row[3]} | Similarity: {row[4]:.4f}")
                            logger.info(f"    {row[5][:100]}...")
                        
        except Exception as e:
            logger.error(f"Error testing search: {e}")


def main():
    """Load all embeddings into Supabase"""
    # Check for required environment variables
    if not os.environ.get('DATABASE_URL'):
        logger.error("DATABASE_URL not found in .env file")
        logger.info("Please ensure your .env file contains:")
        logger.info("DATABASE_URL=postgresql://postgres.xxx:password@aws-0-us-west-1.pooler.supabase.com:5432/postgres")
        sys.exit(1)
    
    # Create loader and process files
    loader = EmbeddingLoader()
    
    # Load all Microsoft 10-K embeddings
    loader.load_all_embeddings()
    
    logger.info("\n✓ Embeddings are now available in Supabase for vector search!")
    logger.info("You can now use semantic search across all Microsoft 10-K filings.")


if __name__ == "__main__":
    main()