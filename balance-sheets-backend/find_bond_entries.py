"""Script to find and list companies that are actually bonds/notes in the database"""
import logging
from database import Database
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_bond_entries():
    """Find companies that appear to be bonds/notes based on their names"""
    db = Database()
    
    # Keywords that indicate bonds/notes
    bond_keywords = [
        '%',           # Percentage signs typically indicate bond yields
        'NTS',         # Notes
        'Notes',
        'Note',
        'Bond',
        'Bonds',
        'Debenture',
        'Debentures',
        'Sr ',         # Senior notes
        'Senior',
        'Subordinated',
        'Convertible',
        'due ',        # Common in bond descriptions
        'Due ',
        'Maturity',
        'Coupon',
        'Fixed Rate',
        'Floating Rate',
        'FRN',         # Floating Rate Note
        'MTN',         # Medium Term Note
        'CP',          # Commercial Paper
        'Pfd',         # Preferred stock (often bond-like)
        'Preferred',
        'Series '      # Often used in bond series
    ]
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Build the WHERE clause with all keywords
                where_conditions = []
                params = []
                
                for keyword in bond_keywords:
                    where_conditions.append("name ILIKE %s")
                    params.append(f'%{keyword}%')
                
                # Also check for patterns like "Company 5.35%" or similar
                where_clause = " OR ".join(where_conditions)
                
                query = f"""
                    SELECT 
                        c.id,
                        c.ticker,
                        c.name,
                        c.sector,
                        c.industry,
                        md.market_cap,
                        COUNT(fs.id) as snapshot_count
                    FROM companies c
                    LEFT JOIN market_data md ON c.id = md.company_id
                    LEFT JOIN financial_snapshots fs ON c.id = fs.company_id
                    WHERE {where_clause}
                    GROUP BY c.id, c.ticker, c.name, c.sector, c.industry, md.market_cap
                    ORDER BY c.name
                """
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                if results:
                    logger.info(f"Found {len(results)} potential bond/note entries:")
                    print("\n" + "="*100)
                    print(f"{'ID':<6} {'Ticker':<15} {'Name':<50} {'Sector':<20} {'Snapshots':<10}")
                    print("="*100)
                    
                    for row in results:
                        id, ticker, name, sector, industry, market_cap, snapshot_count = row
                        print(f"{id:<6} {ticker:<15} {name[:50]:<50} {(sector or 'N/A'):<20} {snapshot_count:<10}")
                    
                    print("="*100)
                    print(f"\nTotal potential bond/note entries found: {len(results)}")
                    
                    # Also show a summary by pattern
                    print("\n\nSummary by pattern:")
                    print("-"*50)
                    for keyword in ['%', 'NTS', 'Notes', 'Bond', 'due', 'Senior', 'Convertible']:
                        count = sum(1 for r in results if keyword.lower() in r[2].lower())
                        if count > 0:
                            print(f"Names containing '{keyword}': {count}")
                    
                else:
                    logger.info("No potential bond/note entries found.")
                
                # Also check for unusual ticker patterns that might indicate bonds
                print("\n\nChecking for unusual tickers...")
                cur.execute("""
                    SELECT ticker, name, sector
                    FROM companies
                    WHERE 
                        LENGTH(ticker) > 10  -- Unusually long tickers
                        OR ticker ~ '[0-9]{4,}'  -- Contains 4+ consecutive digits
                        OR ticker LIKE '%-%'  -- Contains hyphens
                        OR ticker LIKE '%.%'  -- Contains periods
                    ORDER BY ticker
                """)
                
                unusual_tickers = cur.fetchall()
                if unusual_tickers:
                    print(f"\nFound {len(unusual_tickers)} companies with unusual tickers:")
                    print("-"*80)
                    for ticker, name, sector in unusual_tickers:
                        print(f"{ticker:<20} {name[:40]:<40} {(sector or 'N/A'):<20}")
                
                return results
                
    except Exception as e:
        logger.error(f"Error finding bond entries: {e}")
        raise

def delete_bond_entries(company_ids):
    """Delete specified companies and all their related data"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Delete in order due to foreign key constraints
                # First, delete dependent data
                cur.execute("DELETE FROM company_metrics WHERE company_id = ANY(%s)", (company_ids,))
                deleted_metrics = cur.rowcount
                
                cur.execute("DELETE FROM market_data WHERE company_id = ANY(%s)", (company_ids,))
                deleted_market = cur.rowcount
                
                cur.execute("DELETE FROM financial_snapshots WHERE company_id = ANY(%s)", (company_ids,))
                deleted_snapshots = cur.rowcount
                
                cur.execute("DELETE FROM annual_reports WHERE company_id = ANY(%s)", (company_ids,))
                deleted_reports = cur.rowcount
                
                # Finally, delete the companies
                cur.execute("DELETE FROM companies WHERE id = ANY(%s)", (company_ids,))
                deleted_companies = cur.rowcount
                
                conn.commit()
                
                logger.info(f"Deleted {deleted_companies} companies")
                logger.info(f"Deleted {deleted_snapshots} financial snapshots")
                logger.info(f"Deleted {deleted_metrics} company metrics")
                logger.info(f"Deleted {deleted_market} market data entries")
                logger.info(f"Deleted {deleted_reports} annual reports")
                
    except Exception as e:
        logger.error(f"Error deleting bond entries: {e}")
        raise

if __name__ == "__main__":
    # Find potential bond entries
    bond_entries = find_bond_entries()
    
    if bond_entries:
        print("\n\nTo delete these entries, uncomment the following code and run again:")
        print("# company_ids = [entry[0] for entry in bond_entries]")
        print("# delete_bond_entries(company_ids)")