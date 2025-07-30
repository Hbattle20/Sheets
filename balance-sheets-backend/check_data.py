"""Check what data we have in the database"""
from database import Database
from datetime import datetime

db = Database()

with db.get_connection() as conn:
    with conn.cursor() as cur:
        # Get Microsoft's data
        cur.execute("""
            SELECT 
                fs.period_end_date,
                fs.report_type,
                fs.revenue,
                fs.net_income,
                fs.operating_cash_flow,
                fs.free_cash_flow,
                fs.assets,
                fs.equity
            FROM financial_snapshots fs
            JOIN companies c ON fs.company_id = c.id
            WHERE c.ticker = 'MSFT'
            ORDER BY fs.period_end_date DESC
        """)
        
        results = cur.fetchall()
        
        print("\nMicrosoft Financial Data:")
        print("=" * 100)
        print(f"{'Date':<12} {'Type':<6} {'Revenue':<15} {'Net Income':<15} {'Op Cash Flow':<15} {'Free Cash Flow':<15}")
        print("-" * 100)
        
        for row in results:
            date = row[0].strftime('%Y-%m-%d')
            report_type = row[1]
            revenue = f"${float(row[2])/1e9:.1f}B" if row[2] else "N/A"
            net_income = f"${float(row[3])/1e9:.1f}B" if row[3] else "N/A"
            op_cf = f"${float(row[4])/1e9:.1f}B" if row[4] else "N/A"
            free_cf = f"${float(row[5])/1e9:.1f}B" if row[5] else "N/A"
            
            print(f"{date:<12} {report_type:<6} {revenue:<15} {net_income:<15} {op_cf:<15} {free_cf:<15}")