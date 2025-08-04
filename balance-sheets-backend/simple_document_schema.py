"""Simple schema for tracking 10-K documents without vector/embedding complexity"""
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_simple_document_schema():
    """Create a simple schema just for tracking 10-K documents"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Drop the old annual_reports table
                logger.info("Dropping old annual_reports table...")
                cur.execute("DROP TABLE IF EXISTS annual_reports CASCADE")
                
                # Create simple documents table
                logger.info("Creating new documents table...")
                cur.execute("""
                    CREATE TABLE documents (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                        document_type VARCHAR(20) DEFAULT '10-K',
                        fiscal_year INTEGER,
                        filing_date DATE,
                        sec_url TEXT,
                        local_filename TEXT,  -- e.g., 'MSFT_10K_2025-07-30.html'
                        storage_url TEXT,     -- Supabase Storage URL (when we upload)
                        file_size_bytes BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(company_id, document_type, fiscal_year)
                    );
                    
                    CREATE INDEX idx_documents_company_year ON documents(company_id, fiscal_year);
                """)
                
                conn.commit()
                logger.info("✓ Schema created successfully!")
                
        return True
        
    except Exception as e:
        logger.error(f"Schema creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def populate_from_existing_files():
    """Populate the documents table with the 10-K files we already downloaded"""
    import os
    import re
    from datetime import datetime
    
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Find all downloaded 10-K files
                files = [f for f in os.listdir('.') if '_10K_' in f and f.endswith('.html')]
                
                logger.info(f"\nFound {len(files)} 10-K files to track")
                
                for filename in files:
                    # Parse filename: TICKER_10K_YYYY-MM-DD.html
                    match = re.match(r'([A-Z]+)_10K_(\d{4}-\d{2}-\d{2})\.html', filename)
                    if match:
                        ticker = match.group(1)
                        filing_date = datetime.strptime(match.group(2), '%Y-%m-%d')
                        fiscal_year = filing_date.year - 1  # Usually previous fiscal year
                        
                        # Get company ID
                        cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
                        result = cur.fetchone()
                        
                        if result:
                            company_id = result[0]
                            file_size = os.path.getsize(filename)
                            
                            # Insert document record
                            cur.execute("""
                                INSERT INTO documents 
                                (company_id, document_type, fiscal_year, filing_date, 
                                 local_filename, file_size_bytes)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, document_type, fiscal_year) 
                                DO UPDATE SET 
                                    local_filename = EXCLUDED.local_filename,
                                    file_size_bytes = EXCLUDED.file_size_bytes
                                RETURNING id
                            """, (company_id, '10-K', fiscal_year, filing_date, filename, file_size))
                            
                            doc_id = cur.fetchone()[0]
                            logger.info(f"  ✓ {ticker} FY{fiscal_year}: {filename} ({file_size/1024/1024:.1f} MB)")
                
                conn.commit()
                
                # Show summary
                cur.execute("SELECT COUNT(*) FROM documents")
                total = cur.fetchone()[0]
                logger.info(f"\n✓ Tracked {total} documents in database")
                
    except Exception as e:
        logger.error(f"Population failed: {e}")
        import traceback
        traceback.print_exc()


def show_current_documents():
    """Show what documents we have"""
    db = Database()
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.ticker,
                    d.fiscal_year,
                    d.filing_date,
                    d.local_filename,
                    d.file_size_bytes / 1024.0 / 1024.0 as size_mb
                FROM documents d
                JOIN companies c ON d.company_id = c.id
                ORDER BY c.ticker, d.fiscal_year
            """)
            
            results = cur.fetchall()
            
            print("\nCurrent 10-K Documents:")
            print("-" * 80)
            print(f"{'Ticker':6} {'FY':4} {'Filed':12} {'Filename':30} {'Size (MB)':>10}")
            print("-" * 80)
            
            for row in results:
                ticker, fy, filed, filename, size_mb = row
                print(f"{ticker:6} {fy:4} {filed.strftime('%Y-%m-%d'):12} {filename:30} {size_mb:10.1f}")


if __name__ == "__main__":
    logger.info("Creating simple document tracking schema...")
    
    if create_simple_document_schema():
        logger.info("\n✓ Schema created!")
        
        # Populate with existing files
        populate_from_existing_files()
        
        # Show what we have
        show_current_documents()
    else:
        logger.error("\n✗ Schema creation failed!")