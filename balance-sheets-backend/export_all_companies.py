"""Export all companies to a text file for review"""
import csv
from database import Database

def export_companies():
    db = Database()
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get all companies ordered by name
                cur.execute("""
                    SELECT c.ticker, c.name, c.sector, md.market_cap
                    FROM companies c
                    LEFT JOIN market_data md ON c.id = md.company_id
                    ORDER BY c.name
                """)
                
                results = cur.fetchall()
                
                # Write to CSV file for easier review
                with open('all_companies.csv', 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Ticker', 'Name', 'Sector', 'Market Cap'])
                    
                    for ticker, name, sector, market_cap in results:
                        market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
                        writer.writerow([ticker, name, sector or 'N/A', market_cap_str])
                
                # Also write a simple text file with just ticker and name
                with open('all_companies.txt', 'w', encoding='utf-8') as txtfile:
                    txtfile.write(f"Total companies: {len(results)}\n")
                    txtfile.write("="*80 + "\n\n")
                    
                    for ticker, name, sector, market_cap in results:
                        txtfile.write(f"{ticker:10} | {name}\n")
                
                print(f"Exported {len(results)} companies to:")
                print("  - all_companies.csv (full details)")
                print("  - all_companies.txt (simple list)")
                
                # Print some potentially suspicious patterns
                print("\nPotentially suspicious entries to review:")
                print("-" * 60)
                
                suspicious_count = 0
                for ticker, name, sector, market_cap in results:
                    # Check for more patterns that might indicate non-companies
                    if any(pattern in name.upper() for pattern in [
                        'WARRANT', 'RIGHT', 'UNIT', 'TRUST', 'NOTE', 'BOND', 
                        'DEBENTURE', 'SERIES', 'PREFERRED', 'PFD', 'DEP SH',
                        'DEPOSITARY', 'CUMULATIVE', 'PERPETUAL', 'FIXED RATE',
                        'FLOATING', 'CONVERTIBLE', ' NT ', ' NTS ', ' SR ',
                        ' JR ', 'DUE 20', '%'
                    ]):
                        suspicious_count += 1
                        if suspicious_count <= 50:  # Limit output
                            print(f"{ticker:10} | {name[:60]}")
                
                if suspicious_count > 50:
                    print(f"... and {suspicious_count - 50} more suspicious entries")
                
                print(f"\nTotal suspicious entries found: {suspicious_count}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_companies()