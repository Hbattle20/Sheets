"""Upload 10-K HTML files to Supabase Storage"""
import os
import logging
from database import Database
from supabase import create_client, Client
from config import SUPABASE_URL
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the anon key for storage operations
SUPABASE_ANON_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

# Initialize Supabase client
if SUPABASE_URL and SUPABASE_ANON_KEY:
    logger.info(f"Using Supabase URL: {SUPABASE_URL}")
    logger.info(f"Anon key found: {'Yes' if SUPABASE_ANON_KEY else 'No'} (length: {len(SUPABASE_ANON_KEY) if SUPABASE_ANON_KEY else 0})")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
else:
    logger.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
    logger.error(f"SUPABASE_URL: {SUPABASE_URL}")
    logger.error(f"SUPABASE_ANON_KEY: {'Set' if SUPABASE_ANON_KEY else 'Not set'}")
    supabase = None

# Storage bucket name
BUCKET_NAME = "10k-reports"


def check_bucket_exists():
    """Check if the storage bucket exists (assumes it was created in dashboard)"""
    try:
        # Try to list files in the bucket as a way to check it exists
        result = supabase.storage.from_(BUCKET_NAME).list()
        logger.info(f"✓ Bucket '{BUCKET_NAME}' is accessible")
        return True
    except Exception as e:
        logger.error(f"Cannot access bucket '{BUCKET_NAME}': {e}")
        logger.error("Please create the bucket in the Supabase dashboard first")
        return False


def calculate_file_hash(filepath):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def upload_10k_files():
    """Upload all 10-K files to Supabase Storage"""
    db = Database()
    
    # First, check if bucket exists
    if not check_bucket_exists():
        logger.error("Failed to access storage bucket")
        return
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get all documents that need uploading
                cur.execute("""
                    SELECT 
                        d.id,
                        d.local_filename,
                        d.fiscal_year,
                        c.ticker
                    FROM documents d
                    JOIN companies c ON d.company_id = c.id
                    WHERE d.storage_url IS NULL
                    AND d.local_filename IS NOT NULL
                    ORDER BY c.ticker
                """)
                
                documents = cur.fetchall()
                logger.info(f"\nFound {len(documents)} documents to upload")
                
                for doc_id, filename, fiscal_year, ticker in documents:
                    try:
                        # Check if file exists
                        if not os.path.exists(filename):
                            logger.warning(f"✗ File not found: {filename}")
                            continue
                        
                        # Calculate file hash
                        file_hash = calculate_file_hash(filename)
                        
                        # Storage path: ticker_fiscal_year.html (no folders for now)
                        storage_path = f"{ticker}_{fiscal_year}_10K.html"
                        
                        logger.info(f"\nUploading {ticker} FY{fiscal_year}: {filename}")
                        logger.info(f"  Storage path: {storage_path}")
                        
                        # Read file content
                        with open(filename, 'rb') as f:
                            file_content = f.read()
                        
                        # Upload to Supabase Storage
                        result = supabase.storage.from_(BUCKET_NAME).upload(
                            path=storage_path,
                            file=file_content,
                            file_options={
                                "content-type": "text/html"
                            }
                        )
                        
                        # Get public URL
                        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
                        
                        logger.info(f"  ✓ Uploaded successfully")
                        logger.info(f"  Public URL: {public_url}")
                        
                        # Update database with storage URL and hash
                        cur.execute("""
                            UPDATE documents 
                            SET storage_url = %s,
                                file_hash = %s
                            WHERE id = %s
                        """, (public_url, file_hash, doc_id))
                        
                        conn.commit()
                        
                    except Exception as e:
                        logger.error(f"  ✗ Failed to upload {filename}: {e}")
                        continue
                
                # Show summary
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(storage_url) as uploaded
                    FROM documents
                """)
                
                total, uploaded = cur.fetchone()
                logger.info(f"\n{'='*60}")
                logger.info(f"Upload Summary:")
                logger.info(f"  Total documents: {total}")
                logger.info(f"  Uploaded: {uploaded}")
                logger.info(f"  Remaining: {total - uploaded}")
                
    except Exception as e:
        logger.error(f"Upload process failed: {e}")
        import traceback
        traceback.print_exc()


def verify_uploads():
    """Verify uploaded files and show their URLs"""
    db = Database()
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.ticker,
                    d.fiscal_year,
                    d.storage_url,
                    d.file_size_bytes / 1024.0 / 1024.0 as size_mb
                FROM documents d
                JOIN companies c ON d.company_id = c.id
                WHERE d.storage_url IS NOT NULL
                ORDER BY c.ticker
            """)
            
            results = cur.fetchall()
            
            if results:
                print("\nUploaded 10-K Documents:")
                print("-" * 100)
                print(f"{'Ticker':6} {'FY':4} {'Size (MB)':>10} Storage URL")
                print("-" * 100)
                
                for ticker, fy, url, size_mb in results:
                    # Shorten URL for display
                    short_url = url.split('/storage/v1/object/public/')[-1] if url else 'N/A'
                    print(f"{ticker:6} {fy:4} {size_mb:10.1f} {short_url}")
            else:
                print("\nNo documents uploaded yet.")


if __name__ == "__main__":
    logger.info("Starting upload to Supabase Storage...")
    
    # Check if we have Supabase client
    if not supabase:
        logger.error("Supabase client not initialized. Check your .env file.")
    else:
        # Upload files
        upload_10k_files()
        
        # Verify uploads
        print("\n")
        verify_uploads()