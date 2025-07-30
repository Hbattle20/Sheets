"""Setup script to initialize database and fetch initial data"""
import logging
import sys
from datetime import datetime

from database import Database
from pipeline import DataPipeline
from models import DataFetchLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("Balance Sheets Backend - Database Setup")
    print("="*60 + "\n")
    
    # Initialize database connection
    print("1. Testing database connection...")
    db = Database()
    
    if not db.test_connection():
        print("❌ Failed to connect to database. Please check your configuration.")
        print("\nMake sure you have set the following environment variables:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_KEY")
        print("  - FMP_API_KEY")
        sys.exit(1)
    
    print("✅ Database connection successful!\n")
    
    # Create tables
    print("2. Creating database tables...")
    try:
        db.create_tables()
        print("✅ Database tables created successfully!\n")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)
    
    # Initialize pipeline
    print("3. Initializing data pipeline...")
    pipeline = DataPipeline()
    print("✅ Pipeline initialized!\n")
    
    # Check API calls remaining
    calls_today = db.get_api_calls_today()
    print(f"4. API calls used today: {calls_today}/250\n")
    
    # Ask user if they want to fetch Microsoft data
    print("5. Ready to fetch data for Microsoft (MSFT) as a test.")
    print("   This will use approximately 5 API calls.")
    
    response = input("\nDo you want to proceed? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\nFetching data for Microsoft (MSFT)...")
        print("-" * 40)
        
        success = pipeline.process_company('MSFT')
        
        if success:
            print("\n✅ Setup complete! Microsoft data has been stored in your database.")
            
            # Show what's in the database
            print("\n" + "="*60)
            print("Database Contents:")
            print("="*60)
            
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    # Count companies
                    cur.execute("SELECT COUNT(*) FROM companies")
                    company_count = cur.fetchone()[0]
                    print(f"Companies: {company_count}")
                    
                    # Count financial snapshots
                    cur.execute("SELECT COUNT(*) FROM financial_snapshots")
                    snapshot_count = cur.fetchone()[0]
                    print(f"Financial Snapshots: {snapshot_count}")
                    
                    # Count market data entries
                    cur.execute("SELECT COUNT(*) FROM market_data")
                    market_count = cur.fetchone()[0]
                    print(f"Market Data Entries: {market_count}")
                    
                    # Count metrics
                    cur.execute("SELECT COUNT(*) FROM company_metrics")
                    metrics_count = cur.fetchone()[0]
                    print(f"Company Metrics: {metrics_count}")
                    
                    # Count fetch logs
                    cur.execute("SELECT COUNT(*) FROM data_fetch_log")
                    log_count = cur.fetchone()[0]
                    print(f"Fetch Logs: {log_count}")
            
            print("\n🎉 Your Balance Sheets Backend is ready to use!")
            
        else:
            print("\n❌ Failed to fetch Microsoft data. Check the logs above for details.")
    else:
        print("\n✅ Setup complete! Database tables created but no data fetched.")
        print("   You can run the pipeline later to fetch company data.")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("1. To fetch more companies, use the DataPipeline class:")
    print("   pipeline = DataPipeline()")
    print("   pipeline.process_company('AAPL')  # Apple")
    print("   pipeline.process_company('GOOGL') # Google")
    print("\n2. To update market data for existing companies:")
    print("   pipeline.update_market_data('MSFT')")
    print("\n3. Remember you have a limit of 250 API calls per day on the free tier.")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()