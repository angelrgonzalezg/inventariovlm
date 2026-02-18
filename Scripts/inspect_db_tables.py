import sqlite3, os
DB = os.path.join(os.getcwd(), 'inventariovlm.db')
print('DB:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
for (t,) in cur.fetchall():
    print('\nTable:', t)
    try:
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        for c in cols:
            print(' ', c)
    except Exception as e:
        print('  error reading schema', e)
conn.close()
