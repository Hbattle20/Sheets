"""Script to find companies that are definitely bonds/notes based on specific patterns"""
import logging
from database import Database
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_definite_bond_entries():
    """Find companies that are definitely bonds/notes based on specific patterns"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Query for entries with percentage signs in name
                print("\n=== Companies with percentage signs in name ===")
                cur.execute("""
                    SELECT c.id, c.ticker, c.name, c.sector
                    FROM companies c
                    WHERE c.name LIKE '%\\%%' ESCAPE '\\'
                    ORDER BY c.name
                """)
                
                percent_results = cur.fetchall()
                if percent_results:
                    print(f"\nFound {len(percent_results)} companies with % in name:")
                    print("-"*100)
                    for id, ticker, name, sector in percent_results:
                        print(f"ID: {id:<6} Ticker: {ticker:<15} Name: {name}")
                
                # Query for entries with "Notes" or "Bonds" in name
                print("\n\n=== Companies with 'Notes' or 'Bonds' in name ===")
                cur.execute("""
                    SELECT c.id, c.ticker, c.name, c.sector
                    FROM companies c
                    WHERE c.name ~* '\\b(notes?|bonds?|debentures?)\\b'
                       OR c.name ~* '\\bdue\\s+\\d{4}\\b'
                       OR c.name ~* '\\b(senior|subordinated|convertible)\\s+(notes?|bonds?)\\b'
                    ORDER BY c.name
                """)
                
                bond_results = cur.fetchall()
                if bond_results:
                    print(f"\nFound {len(bond_results)} companies with bond/note keywords:")
                    print("-"*100)
                    for id, ticker, name, sector in bond_results:
                        print(f"ID: {id:<6} Ticker: {ticker:<15} Name: {name}")
                
                # Query for entries with numeric patterns typical of bonds
                print("\n\n=== Companies with bond-like numeric patterns ===")
                cur.execute("""
                    SELECT c.id, c.ticker, c.name, c.sector
                    FROM companies c
                    WHERE c.name ~ '\\d+\\.\\d+%'  -- Pattern like "5.35%"
                       OR c.name ~ '\\d{1,2}/\\d{1,2}/\\d{2,4}'  -- Date patterns
                       OR c.name ~ '\\b\\d{4}\\s+(Senior|Subordinated|Notes|Bonds)'  -- Year patterns
                    ORDER BY c.name
                """)
                
                numeric_results = cur.fetchall()
                if numeric_results:
                    print(f"\nFound {len(numeric_results)} companies with bond-like numeric patterns:")
                    print("-"*100)
                    for id, ticker, name, sector in numeric_results:
                        print(f"ID: {id:<6} Ticker: {ticker:<15} Name: {name}")
                
                # Combine all results and remove duplicates
                all_bond_ids = set()
                all_bond_ids.update([r[0] for r in percent_results])
                all_bond_ids.update([r[0] for r in bond_results])
                all_bond_ids.update([r[0] for r in numeric_results])
                
                print(f"\n\n=== SUMMARY ===")
                print(f"Total unique bond/note entries found: {len(all_bond_ids)}")
                print(f"Company IDs: {sorted(list(all_bond_ids))}")
                
                # Get more details about these companies
                if all_bond_ids:
                    print("\n\n=== Detailed information for bond entries ===")
                    cur.execute("""
                        SELECT 
                            c.id,
                            c.ticker,
                            c.name,
                            c.sector,
                            COUNT(fs.id) as snapshot_count,
                            md.market_cap
                        FROM companies c
                        LEFT JOIN financial_snapshots fs ON c.id = fs.company_id
                        LEFT JOIN market_data md ON c.id = md.company_id
                        WHERE c.id = ANY(%s)
                        GROUP BY c.id, c.ticker, c.name, c.sector, md.market_cap
                        ORDER BY c.name
                    """, (list(all_bond_ids),))
                    
                    detailed_results = cur.fetchall()
                    print("-"*120)
                    print(f"{'ID':<6} {'Ticker':<15} {'Name':<60} {'Snapshots':<10} {'Market Cap':<15}")
                    print("-"*120)
                    for id, ticker, name, sector, snapshot_count, market_cap in detailed_results:
                        market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
                        print(f"{id:<6} {ticker:<15} {name[:60]:<60} {snapshot_count:<10} {market_cap_str:<15}")
                
                return list(all_bond_ids)
                
    except Exception as e:
        logger.error(f"Error finding bond entries: {e}")
        raise

def delete_bond_entries(company_ids):
    """Delete specified companies and all their related data"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # First, let's save the names of companies we're deleting for reference
                cur.execute("""
                    SELECT id, ticker, name FROM companies WHERE id = ANY(%s)
                """, (company_ids,))
                companies_to_delete = cur.fetchall()
                
                print("\n=== Companies to be deleted ===")
                for id, ticker, name in companies_to_delete:
                    print(f"ID: {id}, Ticker: {ticker}, Name: {name}")
                
                # Delete in order due to foreign key constraints
                tables_to_clean = [
                    ('user_matches', 'company_id'),
                    ('chat_sessions', 'company_id'),
                    ('company_metrics', 'company_id'),
                    ('market_data', 'company_id'),
                    ('financial_snapshots', 'company_id'),
                    ('annual_reports', 'company_id'),
                    ('data_fetch_log', 'ticker IN (SELECT ticker FROM companies WHERE id = ANY(%s))'),
                ]
                
                for table, condition in tables_to_clean[:-1]:
                    cur.execute(f"DELETE FROM {table} WHERE {condition} = ANY(%s)", (company_ids,))
                    print(f"Deleted {cur.rowcount} rows from {table}")
                
                # Special handling for data_fetch_log (uses ticker)
                cur.execute("""
                    DELETE FROM data_fetch_log 
                    WHERE ticker IN (SELECT ticker FROM companies WHERE id = ANY(%s))
                """, (company_ids,))
                print(f"Deleted {cur.rowcount} rows from data_fetch_log")
                
                # Finally, delete the companies
                cur.execute("DELETE FROM companies WHERE id = ANY(%s)", (company_ids,))
                deleted_companies = cur.rowcount
                
                conn.commit()
                
                print(f"\nSuccessfully deleted {deleted_companies} bond/note entries from the database")
                
    except Exception as e:
        logger.error(f"Error deleting bond entries: {e}")
        raise

if __name__ == "__main__":
    # Find definite bond entries
    bond_ids = find_definite_bond_entries()
    
    if bond_ids:
        print("\n\nTo delete these entries, uncomment the following code and run again:")
        print(f"# delete_bond_entries({bond_ids})")
        
        # Ask for confirmation
        response = input("\n\nDo you want to delete these bond entries? (yes/no): ")
        if response.lower() == 'yes':
            delete_bond_entries(bond_ids)
        else:
            print("Deletion cancelled.")