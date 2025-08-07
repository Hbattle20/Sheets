"""Check Kyndryl historical data"""
from database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
with db.get_connection() as conn:
    with conn.cursor() as cur:
        # Get company info
        cur.execute("SELECT id, name FROM companies WHERE ticker = 'KD'")
        company_id, name = cur.fetchone()
        logger.info(f"Company: {name} (ID: {company_id})")
        
        # Get financial snapshots
        cur.execute("""
            SELECT 
                report_type,
                period_end_date,
                revenue,
                net_income,
                assets,
                liabilities
            FROM financial_snapshots
            WHERE company_id = %s
            ORDER BY period_end_date DESC
        """, (company_id,))
        
        results = cur.fetchall()
        logger.info(f"\nFinancial Snapshots: {len(results)} total")
        logger.info("-" * 80)
        
        for report_type, date, revenue, net_income, assets, liabilities in results:
            # Convert to billions for readability
            rev_b = float(revenue) / 1e9 if revenue else 0
            income_b = float(net_income) / 1e9 if net_income else 0
            assets_b = float(assets) / 1e9 if assets else 0
            liab_b = float(liabilities) / 1e9 if liabilities else 0
            
            logger.info(f"{date} ({report_type}):")
            logger.info(f"  Revenue: ${rev_b:.1f}B")
            logger.info(f"  Net Income: ${income_b:.2f}B")
            logger.info(f"  Assets: ${assets_b:.1f}B")
            logger.info(f"  Liabilities: ${liab_b:.1f}B")
            logger.info("")