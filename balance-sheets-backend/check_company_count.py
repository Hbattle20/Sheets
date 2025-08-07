from database import Database

db = Database()
with db.get_connection() as conn:
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM companies')
    print(f'Remaining companies: {cur.fetchone()[0]}')