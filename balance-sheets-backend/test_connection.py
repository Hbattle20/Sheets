"""Test database connection and debug connection string"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print out what we're getting (masked for security)
db_url = os.getenv('DATABASE_URL')
if db_url:
    # Mask the password for display
    import re
    masked_url = re.sub(r':([^@]+)@', ':****@', db_url)
    print(f"DATABASE_URL found: {masked_url}")
    print(f"URL length: {len(db_url)}")
else:
    print("DATABASE_URL not found in environment")

# Also check other vars
print(f"\nSUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY exists: {'Yes' if os.getenv('SUPABASE_KEY') else 'No'}")
print(f"FMP_API_KEY exists: {'Yes' if os.getenv('FMP_API_KEY') else 'No'}")

# Try to connect
if db_url:
    print("\nTrying to connect...")
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        print("✅ Connection successful!")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")