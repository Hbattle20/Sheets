"""Script to remove the most obvious bond/note entries (those with % in name)"""
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_obvious_bonds():
    """Find companies with % in name - these are clearly bonds/notes"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get companies with % in name
                cur.execute("""
                    SELECT c.id, c.ticker, c.name, md.market_cap
                    FROM companies c
                    LEFT JOIN market_data md ON c.id = md.company_id
                    WHERE c.name LIKE '%\\%%' ESCAPE '\\'
                    ORDER BY c.name
                """)
                
                results = cur.fetchall()
                
                print(f"Found {len(results)} companies with % in name (obvious bonds/notes):")
                print("-" * 100)
                print(f"{'ID':<8} {'Ticker':<15} {'Name':<60} {'Market Cap':<15}")
                print("-" * 100)
                
                ids = []
                for id, ticker, name, market_cap in results:
                    ids.append(id)
                    market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
                    print(f"{id:<8} {ticker:<15} {name[:60]:<60} {market_cap_str:<15}")
                
                return ids
                
    except Exception as e:
        logger.error(f"Error finding bonds: {e}")
        raise

def delete_companies(company_ids):
    """Delete companies and their data"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Delete related data first
                cur.execute("DELETE FROM user_matches WHERE company_id = ANY(%s)", (company_ids,))
                cur.execute("DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE company_id = ANY(%s))", (company_ids,))
                cur.execute("DELETE FROM chat_sessions WHERE company_id = ANY(%s)", (company_ids,))
                cur.execute("DELETE FROM company_metrics WHERE company_id = ANY(%s)", (company_ids,))
                cur.execute("DELETE FROM market_data WHERE company_id = ANY(%s)", (company_ids,))
                cur.execute("DELETE FROM financial_snapshots WHERE company_id = ANY(%s)", (company_ids,))
                # Skip annual_reports table as it doesn't exist
                # cur.execute("DELETE FROM annual_reports WHERE company_id = ANY(%s)", (company_ids,))
                cur.execute("DELETE FROM data_fetch_log WHERE ticker IN (SELECT ticker FROM companies WHERE id = ANY(%s))", (company_ids,))
                
                # Delete companies
                cur.execute("DELETE FROM companies WHERE id = ANY(%s)", (company_ids,))
                deleted = cur.rowcount
                
                conn.commit()
                print(f"\nSuccessfully deleted {deleted} bond entries.")
                
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    bond_ids = find_obvious_bonds()
    
    if bond_ids:
        print(f"\nTotal: {len(bond_ids)} obvious bond entries")
        
        # Check for command line argument
        if len(sys.argv) > 1 and sys.argv[1] == '--delete':
            print("\nDeleting bond entries...")
            delete_companies(bond_ids)
        else:
            print("\nTo delete these entries, run: python clean_obvious_bonds.py --delete")