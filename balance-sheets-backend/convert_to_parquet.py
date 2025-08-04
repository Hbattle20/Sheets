#!/usr/bin/env python3
"""
Convert embedded JSON files to Parquet format
"""

import os
import json
import glob
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
from tqdm import tqdm

def convert_json_to_parquet(json_path):
    """Convert a single embedded JSON file to Parquet"""
    print(f"\nConverting: {json_path}")
    
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chunks = data['chunks']
    
    # Create records for DataFrame
    records = []
    for chunk in chunks:
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
    
    # Create Parquet table
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
    
    # Save Parquet file
    parquet_path = json_path.replace('.json', '.parquet')
    pq.write_table(table, parquet_path, compression='snappy')
    
    # Log file sizes
    json_size = os.path.getsize(json_path) / (1024 * 1024)  # MB
    parquet_size = os.path.getsize(parquet_path) / (1024 * 1024)  # MB
    
    print(f"✓ JSON size: {json_size:.2f} MB")
    print(f"✓ Parquet size: {parquet_size:.2f} MB (compression ratio: {json_size/parquet_size:.1f}x)")
    
    return parquet_path

def main():
    """Convert all embedded JSON files to Parquet"""
    # Find all embedded JSON files
    pattern = "output/MSFT_*/*_embedded.json"
    json_files = glob.glob(pattern)
    
    if not json_files:
        print("No embedded JSON files found")
        return
    
    print(f"Found {len(json_files)} embedded JSON files to convert")
    
    # Convert each file
    parquet_files = []
    for json_file in tqdm(json_files, desc="Converting files"):
        try:
            parquet_path = convert_json_to_parquet(json_file)
            parquet_files.append(parquet_path)
        except Exception as e:
            print(f"\nError converting {json_file}: {e}")
    
    print(f"\n✓ Successfully converted {len(parquet_files)} files to Parquet format")
    
    # Show total size savings
    total_json_size = sum(os.path.getsize(f) / (1024 * 1024) for f in json_files)
    total_parquet_size = sum(os.path.getsize(f) / (1024 * 1024) for f in parquet_files if os.path.exists(f))
    
    print(f"\nTotal JSON size: {total_json_size:.2f} MB")
    print(f"Total Parquet size: {total_parquet_size:.2f} MB")
    print(f"Space saved: {total_json_size - total_parquet_size:.2f} MB ({(1 - total_parquet_size/total_json_size)*100:.1f}%)")

if __name__ == "__main__":
    main()