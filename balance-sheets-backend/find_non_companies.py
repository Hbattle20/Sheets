"""Find and categorize non-company securities in the database"""
from database import Database
from collections import defaultdict

def find_non_companies():
    db = Database()
    
    # Categories of non-companies
    categories = defaultdict(list)
    
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
                    
                    # Rights
                    elif 'RIGHT' in name_upper or ticker.endswith('R'):
                        categories['Rights'].append((id, ticker, name))
                    
                    # Units (often SPACs)
                    elif 'UNIT' in name_upper or ticker.endswith('U'):
                        categories['Units'].append((id, ticker, name))
                    
                    # Acquisition Corps (SPACs)
                    elif 'ACQUISITION CORP' in name_upper or 'SPAC' in name_upper:
                        categories['SPACs'].append((id, ticker, name))
                    
                    # Depositary Shares/Receipts
                    elif 'DEPOSITARY' in name_upper or 'DEPOSITARY SHARE' in name_upper:
                        categories['Depositary'].append((id, ticker, name))
                    
                    # Trusts (REITs are OK, but other trusts might not be)
                    elif 'TRUST' in name_upper and 'REIT' not in name_upper and 'REAL ESTATE' not in name_upper:
                        categories['Trusts'].append((id, ticker, name))
                    
                    # Preferred stocks with specific patterns
                    elif any(pattern in ticker for pattern in ['-P', '.P']) and len(ticker) > 5:
                        categories['Preferred'].append((id, ticker, name))
                    
                    # Notes/Bonds (additional patterns)
                    elif any(pattern in name_upper for pattern in [
                        ' NT ', ' NTS ', ' NOTE', 'BOND', 'DEBENTURE',
                        ' SR ', ' JR ', 'SENIOR', 'JUNIOR', 'SUBORDINATED',
                        'DUE 20', 'FIXED RATE', 'FLOATING RATE'
                    ]):
                        categories['Bonds/Notes'].append((id, ticker, name))
                
                # Print summary
                print("Non-Company Securities Found:")
                print("="*80)
                
                total = 0
                for category, items in sorted(categories.items()):
                    print(f"\n{category}: {len(items)} entries")
                    print("-"*60)
                    # Show first 10 of each category
                    for i, (id, ticker, name) in enumerate(items[:10]):
                        print(f"  {id:6} | {ticker:10} | {name[:50]}")
                    if len(items) > 10:
                        print(f"  ... and {len(items) - 10} more")
                    total += len(items)
                
                print(f"\n{'='*80}")
                print(f"Total non-company securities found: {total}")
                print(f"Total companies in database: {len(results)}")
                print(f"Percentage that are non-companies: {total/len(results)*100:.1f}%")
                
                # Export full list to file
                with open('non_company_securities.txt', 'w') as f:
                    f.write("Non-Company Securities in Database\n")
                    f.write("="*80 + "\n\n")
                    
                    for category, items in sorted(categories.items()):
                        f.write(f"{category}: {len(items)} entries\n")
                        f.write("-"*60 + "\n")
                        for id, ticker, name in sorted(items):
                            f.write(f"{id:6} | {ticker:10} | {name}\n")
                        f.write("\n")
                
                print(f"\nFull list exported to: non_company_securities.txt")
                
                # Create SQL to delete these
                all_ids = []
                for items in categories.values():
                    all_ids.extend([id for id, _, _ in items])
                
                with open('delete_non_companies.sql', 'w') as f:
                    f.write("-- SQL to delete non-company securities\n")
                    f.write(f"-- Total: {len(all_ids)} entries\n\n")
                    f.write("BEGIN;\n\n")
                    f.write("-- Delete related data first\n")
                    f.write(f"DELETE FROM user_matches WHERE company_id IN ({','.join(map(str, all_ids))});\n")
                    f.write(f"DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE company_id IN ({','.join(map(str, all_ids))}));\n")
                    f.write(f"DELETE FROM chat_sessions WHERE company_id IN ({','.join(map(str, all_ids))});\n")
                    f.write(f"DELETE FROM company_metrics WHERE company_id IN ({','.join(map(str, all_ids))});\n")
                    f.write(f"DELETE FROM market_data WHERE company_id IN ({','.join(map(str, all_ids))});\n")
                    f.write(f"DELETE FROM financial_snapshots WHERE company_id IN ({','.join(map(str, all_ids))});\n")
                    f.write(f"DELETE FROM data_fetch_log WHERE ticker IN (SELECT ticker FROM companies WHERE id IN ({','.join(map(str, all_ids))}));\n")
                    f.write(f"\n-- Delete companies\n")
                    f.write(f"DELETE FROM companies WHERE id IN ({','.join(map(str, all_ids))});\n")
                    f.write("\nCOMMIT;\n")
                
                print(f"SQL delete script created: delete_non_companies.sql")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_non_companies()