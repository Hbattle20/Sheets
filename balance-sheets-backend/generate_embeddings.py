#!/usr/bin/env python3
"""
Generate OpenAI embeddings for 10-K chunks with batch processing and cost control.
Supports resume capability and saves in both JSON and Parquet formats.
"""

import os
import json
import glob
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
from tqdm import tqdm
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSION = 3072  # Dimension for text-embedding-3-large
BATCH_SIZE = 2048  # Max batch size for OpenAI API
SAVE_INTERVAL = 100  # Save progress every N chunks
MAX_WORKERS = 5  # Concurrent API requests

# Pricing (as of 2024)
COST_PER_1K_TOKENS = 0.00013  # $0.13 per 1M tokens for text-embedding-3-large
APPROX_TOKENS_PER_WORD = 1.3  # Approximate token to word ratio
COST_THRESHOLD = 0.10  # Ask for confirmation if cost exceeds this


class EmbeddingGenerator:
    """Generate embeddings for 10-K chunks with batch processing"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            # Will use OPENAI_API_KEY environment variable
            self.client = OpenAI()
        
        self.total_cost = 0.0
        self.processed_chunks = 0
        self.resume_file = "embedding_progress.pkl"
    
    def estimate_cost(self, chunks: List[Dict]) -> float:
        """Estimate the cost of embedding all chunks"""
        total_words = sum(chunk['metadata']['word_count'] for chunk in chunks)
        estimated_tokens = total_words * APPROX_TOKENS_PER_WORD
        estimated_cost = (estimated_tokens / 1000) * COST_PER_1K_TOKENS
        return estimated_cost
    
    def load_progress(self) -> Dict:
        """Load previous progress if available"""
        if os.path.exists(self.resume_file):
            try:
                with open(self.resume_file, 'rb') as f:
                    progress = pickle.load(f)
                logger.info(f"Loaded progress: {progress['processed_count']} chunks already processed")
                return progress
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        return {'processed_chunks': {}, 'processed_count': 0}
    
    def save_progress(self, progress: Dict):
        """Save current progress"""
        try:
            with open(self.resume_file, 'wb') as f:
                pickle.dump(progress, f)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
    def generate_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            
            # Calculate cost for this batch
            total_tokens = response.usage.total_tokens
            batch_cost = (total_tokens / 1000) * COST_PER_1K_TOKENS
            self.total_cost += batch_cost
            
            # Extract embeddings in order
            embeddings = [data.embedding for data in response.data]
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def process_chunks_file(self, file_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
        """Process a single chunks file and generate embeddings"""
        logger.info(f"\nProcessing: {file_path}")
        
        # Load chunks
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data['chunks']
        metadata = data['metadata']
        
        # Load progress
        progress = self.load_progress()
        processed_chunks = progress.get('processed_chunks', {})
        
        # Filter out already processed chunks
        chunks_to_process = []
        chunks_with_embeddings = []
        
        for chunk in chunks:
            chunk_id = chunk['metadata']['chunk_id']
            
            if chunk_id in processed_chunks:
                # Already processed, use saved embedding
                chunk['embedding'] = processed_chunks[chunk_id]
                chunks_with_embeddings.append(chunk)
            else:
                chunks_to_process.append(chunk)
        
        if not chunks_to_process:
            logger.info("All chunks already processed!")
        else:
            # Estimate cost for remaining chunks
            estimated_cost = self.estimate_cost(chunks_to_process)
            logger.info(f"Chunks to process: {len(chunks_to_process)}")
            logger.info(f"Estimated cost: ${estimated_cost:.4f}")
            
            # Check if cost exceeds threshold
            if estimated_cost > COST_THRESHOLD:
                response = input(f"\n⚠️  Estimated cost (${estimated_cost:.4f}) exceeds ${COST_THRESHOLD}. Continue? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Processing cancelled by user")
                    return None, None
            
            # Process in batches with progress bar
            pbar = tqdm(total=len(chunks_to_process), desc="Generating embeddings")
            
            for i in range(0, len(chunks_to_process), BATCH_SIZE):
                batch = chunks_to_process[i:i + BATCH_SIZE]
                texts = [chunk['text'] for chunk in batch]
                
                try:
                    # Generate embeddings for batch
                    embeddings = self.generate_embedding_batch(texts)
                    
                    # Add embeddings to chunks
                    for chunk, embedding in zip(batch, embeddings):
                        chunk['embedding'] = embedding
                        chunks_with_embeddings.append(chunk)
                        
                        # Update progress
                        chunk_id = chunk['metadata']['chunk_id']
                        processed_chunks[chunk_id] = embedding
                        self.processed_chunks += 1
                    
                    # Update progress bar
                    pbar.update(len(batch))
                    pbar.set_postfix({'cost': f'${self.total_cost:.4f}'})
                    
                    # Save progress periodically
                    if self.processed_chunks % SAVE_INTERVAL == 0:
                        progress = {
                            'processed_chunks': processed_chunks,
                            'processed_count': len(processed_chunks)
                        }
                        self.save_progress(progress)
                        logger.info(f"Progress saved: {len(processed_chunks)} total chunks processed")
                    
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    pbar.close()
                    raise
            
            pbar.close()
        
        # Sort chunks by original index
        chunks_with_embeddings.sort(key=lambda x: x['metadata']['chunk_index'])
        
        # Prepare output data
        output_data = {
            'metadata': {
                **metadata,
                'embedding_model': EMBEDDING_MODEL,
                'embedding_dimension': EMBEDDING_DIMENSION,
                'processing_date': datetime.now().isoformat(),
                'total_cost': self.total_cost
            },
            'sections': data.get('sections', []),
            'chunks': chunks_with_embeddings
        }
        
        # Determine output paths
        if output_dir is None:
            output_dir = os.path.dirname(file_path)
        
        base_name = os.path.basename(file_path).replace('.json', '')
        json_path = os.path.join(output_dir, f"{base_name}_embedded.json")
        parquet_path = os.path.join(output_dir, f"{base_name}_embedded.parquet")
        
        # Save JSON
        logger.info(f"Saving JSON to: {json_path}")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        # Prepare and save Parquet
        logger.info(f"Saving Parquet to: {parquet_path}")
        
        # Create DataFrame for Parquet
        records = []
        for chunk in chunks_with_embeddings:
            record = {
                'chunk_id': chunk['metadata']['chunk_id'],
                'chunk_index': chunk['metadata']['chunk_index'],
                'section': chunk['metadata']['section'],
                'text': chunk['text'],
                'embedding': chunk['embedding'],
                'word_count': chunk['metadata']['word_count'],
                'ticker': chunk['metadata']['ticker'],
                'filing_date': chunk['metadata']['filing_date']
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Convert embeddings to numpy array for efficient storage
        embeddings_array = np.array(df['embedding'].tolist())
        
        # Create Parquet table with proper schema
        # Store embeddings as a list column (PyArrow will handle efficiently)
        table = pa.table({
            'chunk_id': df['chunk_id'].values,
            'chunk_index': df['chunk_index'].values,
            'section': df['section'].values,
            'text': df['text'].values,
            'embedding': df['embedding'].tolist(),  # Store as list of lists
            'word_count': df['word_count'].values,
            'ticker': df['ticker'].values,
            'filing_date': df['filing_date'].values
        })
        
        pq.write_table(table, parquet_path, compression='snappy')
        
        # Log file sizes
        json_size = os.path.getsize(json_path) / (1024 * 1024)  # MB
        parquet_size = os.path.getsize(parquet_path) / (1024 * 1024)  # MB
        
        logger.info(f"JSON size: {json_size:.2f} MB")
        logger.info(f"Parquet size: {parquet_size:.2f} MB (compression ratio: {json_size/parquet_size:.1f}x)")
        
        return json_path, parquet_path
    
    def process_all_years(self, base_dir: str = "output", ticker: str = "MSFT"):
        """Process all years of 10-K chunks for a given ticker"""
        pattern = os.path.join(base_dir, f"{ticker}_*", f"{ticker}_10K_chunks_*.json")
        chunk_files = glob.glob(pattern)
        
        # Exclude already embedded files
        chunk_files = [f for f in chunk_files if '_embedded' not in f]
        
        if not chunk_files:
            logger.error(f"No chunk files found matching pattern: {pattern}")
            return
        
        logger.info(f"Found {len(chunk_files)} files to process")
        
        # Sort by year
        chunk_files.sort()
        
        results = []
        for file_path in chunk_files:
            try:
                json_path, parquet_path = self.process_chunks_file(file_path)
                if json_path:
                    results.append({
                        'source': file_path,
                        'json': json_path,
                        'parquet': parquet_path
                    })
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        # Clean up progress file
        if os.path.exists(self.resume_file):
            os.remove(self.resume_file)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("EMBEDDING GENERATION COMPLETE")
        logger.info("="*60)
        logger.info(f"Files processed: {len(results)}")
        logger.info(f"Total cost: ${self.total_cost:.4f}")
        logger.info(f"Total chunks processed: {self.processed_chunks}")
        
        if results:
            logger.info("\nOutput files:")
            for result in results:
                logger.info(f"  - {result['parquet']}")


def main():
    """Generate embeddings for all Microsoft 10-K chunks"""
    import sys
    
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("Please set OPENAI_API_KEY environment variable")
        logger.info("Make sure your .env file contains: OPENAI_API_KEY=sk-...")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f".env file exists: {os.path.exists('.env')}")
        sys.exit(1)
    
    # Check dependencies
    try:
        import pandas
        import pyarrow
        import openai
        import tqdm
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install: pip install openai pandas pyarrow tqdm")
        sys.exit(1)
    
    # Create generator and process files
    generator = EmbeddingGenerator()
    
    # Process all Microsoft 10-K files
    generator.process_all_years()


if __name__ == "__main__":
    main()