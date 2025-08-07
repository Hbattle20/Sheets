"""
Remove non-company securities (bonds, preferred stocks, warrants, etc.) from the database
"""
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of 74 securities to remove
SECURITIES_TO_REMOVE = {
    # Preferred Stocks
    'ACP-PA', 'BC-PA', 'BC-PB', 'BC-PC', 'BIP-PA', 'BIP-PB', 'BIP-PC', 
    'BML-PG', 'BML-PH', 'BML-PJ', 'BML-PL', 'BPOP-PB', 'BPOP-PC', 'BRG-PA', 
    'BRG-PC', 'BRG-PD', 'EP-PC', 'FNB-PE', 'GL-PC', 'GL-PD', 'GNL-PA', 
    'GNL-PB', 'RF-PB', 'RF-PC', 'RF-PE', 'SCE-PB', 'SCE-PC', 'SCE-PD', 
    'SCE-PE', 'SCE-PG', 'SCE-PH', 'SCE-PJ', 'SCE-PK', 'SCE-PL', 'SCE-PM', 
    'SCE-PN', 'SR-PA', 'STT-PC', 'STT-PD', 'STT-PE', 'STT-PG', 'USB-PA', 
    'USB-PH', 'USB-PP', 'USB-PQ', 'USB-PR', 'USB-PS', 'WRB-PE', 'WRB-PF', 
    'WRB-PG', 'WRB-PH',
    
    # Warrants
    'BULLW', 'PNTGW', 'VAL-WT', 'VAPEW',
    
    # Rights
    'AACBR', 'COLA', 'GENVR',
    
    # Units
    'AACBU', 'ACACU', 'CLVRU', 'DAAQU', 'GPACU', 'TVACU',
    
    # Bonds/Notes
    'ENJ', 'ENO', 'RZC', 'SOJE', 'SOJB', 'SOJC', 'SOJD', 'SOJE', 'ZTR',
    
    # Other securities
    'ARM', 'HDL', 'PDM', 'PONY'
}

def remove_securities():
    """Remove non-company securities from the database"""
    db = Database()
    
    logger.info(f"Starting removal of {len(SECURITIES_TO_REMOVE)} non-company securities")
    
    removed_count = 0
    failed_removals = []
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            for ticker in SECURITIES_TO_REMOVE:
                try:
                    # Get company ID first
                    cur.execute("SELECT id, name FROM companies WHERE ticker = %s", (ticker,))
                    result = cur.fetchone()
                    
                    if result:
                        company_id, name = result
                        logger.info(f"Removing {ticker} - {name}")
                        
                        # Delete in order to respect foreign key constraints
                        # 1. Delete from company_metrics (references financial_snapshots)
                        cur.execute("""
                            DELETE FROM company_metrics 
                            WHERE snapshot_id IN (
                                SELECT id FROM financial_snapshots WHERE company_id = %s
                            )
                        """, (company_id,))
                        
                        # 2. Delete from financial_snapshots
                        cur.execute("DELETE FROM financial_snapshots WHERE company_id = %s", (company_id,))
                        
                        # 3. Delete from market_data
                        cur.execute("DELETE FROM market_data WHERE company_id = %s", (company_id,))
                        
                        # 4. Delete from data_fetch_log (skip if doesn't exist)
                        try:
                            cur.execute("DELETE FROM data_fetch_log WHERE ticker = %s", (ticker,))
                        except:
                            pass  # Table might not have this ticker
                        
                        # 5. Delete from user_matches (if any)
                        cur.execute("DELETE FROM user_matches WHERE company_id = %s", (company_id,))
                        
                        # 6. Delete from chat_sessions (if any)
                        cur.execute("DELETE FROM chat_sessions WHERE company_id = %s", (company_id,))
                        
                        # 7. Finally delete from companies
                        cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))
                        
                        conn.commit()
                        removed_count += 1
                        logger.info(f"✓ Successfully removed {ticker}")
                    else:
                        logger.info(f"⚠ {ticker} not found in database")
                        
                except Exception as e:
                    conn.rollback()
                    logger.error(f"✗ Failed to remove {ticker}: {str(e)}")
                    failed_removals.append(ticker)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info(f"Removal Summary:")
    logger.info(f"Total securities to remove: {len(SECURITIES_TO_REMOVE)}")
    logger.info(f"Successfully removed: {removed_count}")
    logger.info(f"Not found in database: {len(SECURITIES_TO_REMOVE) - removed_count - len(failed_removals)}")
    logger.info(f"Failed to remove: {len(failed_removals)}")
    
    if failed_removals:
        logger.error(f"Failed removals: {', '.join(failed_removals)}")
    
    # Show current stats
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM companies")
            company_count = cur.fetchone()[0]
            logger.info(f"\nRemaining companies in database: {company_count}")

if __name__ == "__main__":
    remove_securities()