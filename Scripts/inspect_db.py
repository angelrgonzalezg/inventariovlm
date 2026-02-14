import sqlite3
DB = 'inventariovlm.db'
print('DB:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('\nPRAGMA table_info(inventory_count):')
for row in cur.execute("PRAGMA table_info(inventory_count)"):
    print(row)

print('\nCOUNT:')
try:
    cur.execute('SELECT COUNT(*) FROM inventory_count')
    print(cur.fetchone())
except Exception as e:
    print('Error counting rows:', e)

print('\nCOLUMNS via SELECT * LIMIT 1:')
try:
    cur.execute('SELECT * FROM inventory_count LIMIT 1')
    row = cur.fetchone()
    if row is None:
        print('No rows')
    else:
        print('Row length:', len(row))
        print('Row sample:', row)
        # column names
        names = [d[0] for d in cur.description]
        print('Column names:', names)
except Exception as e:
    print('Error selecting rows:', e)

conn.close()
print('\nDone')
