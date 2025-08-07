"""Remove all non-company securities from the database"""
import logging
from database import Database
from find_non_companies import find_non_companies
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_non_company_ids():
    """Get all non-company IDs from the database"""
    db = Database()
    categories = defaultdict(list)
    all_ids = []
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, ticker, name, sector
                    FROM companies
                    ORDER BY name
                """)
                
                results = cur.fetchall()
                
                for id, ticker, name, sector in results:
                    name_upper = name.upper()
                    
                    # Warrants
                    if 'WARRANT' in name_upper or ticker.endswith('W'):
                        categories['Warrants'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Rights
                    elif 'RIGHT' in name_upper or ticker.endswith('R'):
                        categories['Rights'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Units (often SPACs)
                    elif 'UNIT' in name_upper or ticker.endswith('U'):
                        categories['Units'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Acquisition Corps (SPACs)
                    elif 'ACQUISITION CORP' in name_upper or 'SPAC' in name_upper:
                        categories['SPACs'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Depositary Shares/Receipts
                    elif 'DEPOSITARY' in name_upper or 'DEPOSITARY SHARE' in name_upper:
                        categories['Depositary'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Trusts (REITs are OK, but other trusts might not be)
                    elif 'TRUST' in name_upper and 'REIT' not in name_upper and 'REAL ESTATE' not in name_upper:
                        categories['Trusts'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Preferred stocks with specific patterns
                    elif any(pattern in ticker for pattern in ['-P', '.P']) and len(ticker) > 5:
                        categories['Preferred'].append((id, ticker, name))
                        all_ids.append(id)
                    
                    # Notes/Bonds (additional patterns)
                    elif any(pattern in name_upper for pattern in [
                        ' NT ', ' NTS ', ' NOTE', 'BOND', 'DEBENTURE',
                        ' SR ', ' JR ', 'SENIOR', 'JUNIOR', 'SUBORDINATED',
                        'DUE 20', 'FIXED RATE', 'FLOATING RATE'
                    ]):
                        categories['Bonds/Notes'].append((id, ticker, name))
                        all_ids.append(id)
                
                # Remove duplicates
                all_ids = list(set(all_ids))
                
                # Print summary
                logger.info(f"Found {len(all_ids)} non-company securities to remove")
                for category, items in sorted(categories.items()):
                    logger.info(f"  {category}: {len(items)} entries")
                
                return all_ids, categories
                
    except Exception as e:
        logger.error(f"Error finding non-companies: {e}")
        raise

def delete_non_companies(company_ids):
    """Delete companies and their data in batches"""
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Process in batches of 100 to avoid query size limits
                batch_size = 100
                total_deleted = 0
                
                for i in range(0, len(company_ids), batch_size):
                    batch = company_ids[i:i+batch_size]
                    logger.info(f"Processing batch {i//batch_size + 1} of {(len(company_ids)-1)//batch_size + 1}")
                    
                    # Delete related data first
                    cur.execute("DELETE FROM user_matches WHERE company_id = ANY(%s)", (batch,))
                    cur.execute("DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE company_id = ANY(%s))", (batch,))
                    cur.execute("DELETE FROM chat_sessions WHERE company_id = ANY(%s)", (batch,))
                    cur.execute("DELETE FROM company_metrics WHERE company_id = ANY(%s)", (batch,))
                    cur.execute("DELETE FROM market_data WHERE company_id = ANY(%s)", (batch,))
                    cur.execute("DELETE FROM financial_snapshots WHERE company_id = ANY(%s)", (batch,))
                    cur.execute("DELETE FROM data_fetch_log WHERE ticker IN (SELECT ticker FROM companies WHERE id = ANY(%s))", (batch,))
                    
                    # Delete companies
                    cur.execute("DELETE FROM companies WHERE id = ANY(%s)", (batch,))
                    deleted = cur.rowcount
                    total_deleted += deleted
                    
                    conn.commit()
                    logger.info(f"  Deleted {deleted} companies in this batch")
                
                logger.info(f"\nSuccessfully deleted {total_deleted} non-company entries total")
                
                # Check remaining count
                cur.execute("SELECT COUNT(*) FROM companies")
                remaining = cur.fetchone()[0]
                logger.info(f"Remaining companies in database: {remaining}")
                
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        raise

if __name__ == "__main__":
    logger.info("Starting removal of all non-company securities...")
    
    # Get all non-company IDs
    company_ids, categories = get_non_company_ids()
    
    if company_ids:
        # Confirm deletion
        logger.info(f"\nReady to delete {len(company_ids)} non-company securities")
        logger.info("This will permanently remove these entries from the database")
        
        # Proceed with deletion
        delete_non_companies(company_ids)
        
        logger.info("\nDeletion complete!")
    else:
        logger.info("No non-company securities found to delete")