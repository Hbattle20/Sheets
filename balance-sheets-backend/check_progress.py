"""Check batch fetch progress"""
from database import Database

db = Database()

with db.get_connection() as conn:
    with conn.cursor() as cur:
        # Count companies
        cur.execute('SELECT COUNT(DISTINCT ticker) FROM companies')
        total = cur.fetchone()[0]
        
        # Get company list
        cur.execute('SELECT ticker, name FROM companies ORDER BY id')
        companies = cur.fetchall()
        
        print(f"\nTotal companies in database: {total}")
        print("\nCompanies loaded:")
        print("-" * 50)
        for ticker, name in companies:
            print(f"{ticker:6} - {name}")

# Check API usage
calls = db.get_api_calls_today()
print(f"\nAPI calls used today: {calls}/250")
print(f"Remaining calls: {250 - calls}")