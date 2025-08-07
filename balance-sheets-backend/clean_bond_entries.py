"""Comprehensive script to find and remove all bond/note/preferred stock entries from the database"""
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_all_bond_like_entries():
    """Find all bond, note, and preferred stock entries"""
    db = Database()
    all_ids = set()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Companies with percentage signs (bonds/notes with yields)
                cur.execute("""
                    SELECT c.id, c.ticker, c.name
                    FROM companies c
                    WHERE c.name LIKE '%\\%%' ESCAPE '\\'
                """)
                percent_results = cur.fetchall()
                percent_ids = [r[0] for r in percent_results]
                all_ids.update(percent_ids)
                print(f"\n1. Found {len(percent_ids)} companies with % in name (bonds/notes with yields)")
                
                # 2. Companies with bond/note keywords
                cur.execute("""
                    SELECT c.id, c.ticker, c.name
                    FROM companies c
                    WHERE c.name ~* '\\b(notes?|bonds?|debentures?)\\b'
                       OR c.name ~* '\\bdue\\s+\\d{4}\\b'
                       OR c.name ~* '\\b(senior|subordinated|convertible)\\s+(notes?|bonds?)\\b'
                       OR c.name LIKE '%NTS%' OR c.name LIKE '%NTB%' OR c.name LIKE '%NT %'
                       OR c.name LIKE '%SR %' OR c.name LIKE '%JR %'
                       OR c.name LIKE '%JRSUB%' OR c.name LIKE '%SRSUB%'
                """)
                bond_results = cur.fetchall()
                bond_ids = [r[0] for r in bond_results]
                all_ids.update(bond_ids)
                print(f"2. Found {len(bond_ids)} companies with bond/note keywords")
                
                # 3. Preferred stocks (ticker ends with -P followed by letter)
                cur.execute("""
                    SELECT c.id, c.ticker, c.name
                    FROM companies c
                    WHERE c.ticker LIKE '%-P%'
                       OR c.name LIKE '%PFD%'
                       OR c.name LIKE '%Preferred%'
                       OR c.name LIKE '%PREFERRED%'
                """)
                preferred_results = cur.fetchall()
                preferred_ids = [r[0] for r in preferred_results]
                all_ids.update(preferred_ids)
                print(f"3. Found {len(preferred_ids)} preferred stock entries")
                
                # 4. Warrants and units (more specific to avoid false positives)
                cur.execute("""
                    SELECT c.id, c.ticker, c.name
                    FROM companies c
                    WHERE c.name ~* '\\b(warrant|warrants|unit|units|rights)\\b'
                       OR c.ticker LIKE '%.WS' OR c.ticker LIKE '%.UN'
                       OR c.ticker LIKE '%.WT' OR c.ticker LIKE '%.RT'
                """)
                warrant_results = cur.fetchall()
                warrant_ids = [r[0] for r in warrant_results]
                all_ids.update(warrant_ids)
                print(f"4. Found {len(warrant_ids)} warrant/unit entries")
                
                # Get detailed info for all identified entries
                if all_ids:
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
                        ORDER BY c.ticker
                    """, (list(all_ids),))
                    
                    detailed_results = cur.fetchall()
                    
                    print(f"\n{'='*120}")
                    print(f"TOTAL BOND-LIKE ENTRIES FOUND: {len(all_ids)}")
                    print(f"{'='*120}")
                    
                    # Group by type for summary
                    bond_types = {
                        'Bonds/Notes with %': [],
                        'Other Bonds/Notes': [],
                        'Preferred Stocks': [],
                        'Warrants/Units': []
                    }
                    
                    for id, ticker, name, sector, snapshot_count, market_cap in detailed_results:
                        if '%' in name:
                            bond_types['Bonds/Notes with %'].append((id, ticker, name))
                        elif ticker.startswith('-P') or 'PFD' in name or 'Preferred' in name.title():
                            bond_types['Preferred Stocks'].append((id, ticker, name))
                        elif 'warrant' in name.lower() or 'unit' in name.lower() or ticker.endswith('W') or ticker.endswith('U'):
                            bond_types['Warrants/Units'].append((id, ticker, name))
                        else:
                            bond_types['Other Bonds/Notes'].append((id, ticker, name))
                    
                    # Print summary by type
                    for bond_type, entries in bond_types.items():
                        if entries:
                            print(f"\n{bond_type} ({len(entries)} entries):")
                            print("-" * 100)
                            for id, ticker, name in entries[:10]:  # Show first 10
                                print(f"ID: {id:<6} Ticker: {ticker:<15} Name: {name[:60]}")
                            if len(entries) > 10:
                                print(f"... and {len(entries) - 10} more")
                    
                return list(all_ids)
                
    except Exception as e:
        logger.error(f"Error finding bond entries: {e}")
        raise

def delete_bond_entries(company_ids):
    """Delete specified companies and all their related data"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                print(f"\nPreparing to delete {len(company_ids)} bond-like entries...")
                
                # Delete in order due to foreign key constraints
                tables_to_clean = [
                    ('user_matches', 'company_id'),
                    ('chat_sessions', 'company_id'),
                    ('chat_messages', 'company_id IN (SELECT id FROM chat_sessions WHERE company_id = ANY(%s))'),
                    ('company_metrics', 'company_id'),
                    ('market_data', 'company_id'),
                    ('financial_snapshots', 'company_id'),
                    ('annual_reports', 'company_id'),
                ]
                
                total_deleted = 0
                for table, condition in tables_to_clean:
                    if 'chat_messages' in table:
                        # Special handling for chat_messages
                        cur.execute("""
                            DELETE FROM chat_messages 
                            WHERE session_id IN (
                                SELECT id FROM chat_sessions WHERE company_id = ANY(%s)
                            )
                        """, (company_ids,))
                    else:
                        cur.execute(f"DELETE FROM {table} WHERE {condition} = ANY(%s)", (company_ids,))
                    
                    deleted = cur.rowcount
                    total_deleted += deleted
                    if deleted > 0:
                        print(f"  - Deleted {deleted} rows from {table}")
                
                # Delete from data_fetch_log (uses ticker)
                cur.execute("""
                    DELETE FROM data_fetch_log 
                    WHERE ticker IN (SELECT ticker FROM companies WHERE id = ANY(%s))
                """, (company_ids,))
                if cur.rowcount > 0:
                    print(f"  - Deleted {cur.rowcount} rows from data_fetch_log")
                
                # Finally, delete the companies
                cur.execute("DELETE FROM companies WHERE id = ANY(%s)", (company_ids,))
                deleted_companies = cur.rowcount
                
                conn.commit()
                
                print(f"\n{'='*60}")
                print(f"Successfully deleted {deleted_companies} bond/note/preferred entries")
                print(f"Total rows deleted across all tables: {total_deleted + deleted_companies}")
                print(f"{'='*60}")
                
    except Exception as e:
        logger.error(f"Error deleting bond entries: {e}")
        raise

def get_game_ready_companies():
    """Get count of companies that are suitable for the game (not bonds/notes/preferred)"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Count companies that are NOT bonds/notes/preferred
                cur.execute("""
                    SELECT COUNT(DISTINCT c.id)
                    FROM companies c
                    WHERE c.name NOT LIKE '%\\%%' ESCAPE '\\'
                      AND c.ticker NOT LIKE '%-P%'
                      AND c.name NOT LIKE '%NTS%'
                      AND c.name NOT LIKE '%Notes%'
                      AND c.name NOT LIKE '%Bond%'
                      AND c.name NOT LIKE '%Warrant%'
                      AND c.name NOT LIKE '%Unit%'
                      AND c.name NOT LIKE '%PFD%'
                      AND c.name NOT LIKE '%Preferred%'
                """)
                
                result = cur.fetchone()
                return result[0] if result else 0
                
    except Exception as e:
        logger.error(f"Error counting game-ready companies: {e}")
        raise

if __name__ == "__main__":
    # Find all bond-like entries
    bond_ids = find_all_bond_like_entries()
    
    if bond_ids:
        # Show current state
        print(f"\n\nCurrent database state:")
        print(f"- Total companies in database: Check with separate query")
        print(f"- Bond-like entries to remove: {len(bond_ids)}")
        print(f"- Game-ready companies remaining: {get_game_ready_companies()}")
        
        # Ask for confirmation
        print("\n" + "="*60)
        response = input("Do you want to delete these bond/note/preferred entries? (yes/no): ")
        if response.lower() == 'yes':
            delete_bond_entries(bond_ids)
            print(f"\nAfter deletion, game-ready companies: {get_game_ready_companies()}")
        else:
            print("Deletion cancelled.")
    else:
        print("No bond-like entries found.")