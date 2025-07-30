"""Add cash flow columns to existing database"""
from database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_cash_flow_columns():
    """Add operating_cash_flow and free_cash_flow columns to financial_snapshots table"""
    db = Database()
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # Add operating_cash_flow column if it doesn't exist
                cur.execute("""
                    ALTER TABLE financial_snapshots 
                    ADD COLUMN IF NOT EXISTS operating_cash_flow NUMERIC(20, 2)
                """)
                
                # Add free_cash_flow column if it doesn't exist
                cur.execute("""
                    ALTER TABLE financial_snapshots 
                    ADD COLUMN IF NOT EXISTS free_cash_flow NUMERIC(20, 2)
                """)
                
                conn.commit()
                logger.info("Successfully added cash flow columns to financial_snapshots table")
                
            except Exception as e:
                logger.error(f"Error adding columns: {e}")
                raise

if __name__ == "__main__":
    print("Adding cash flow columns to database...")
    add_cash_flow_columns()
    print("Done!")