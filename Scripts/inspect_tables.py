import sqlite3

DB='inventariovlm.db'
conn=sqlite3.connect(DB)
cur=conn.cursor()
print('PRAGMA table_info(deposits)')
for r in cur.execute("PRAGMA table_info(deposits)"):
    print(r)
print('\nPRAGMA table_info(racks)')
for r in cur.execute("PRAGMA table_info(racks)"):
    print(r)
print('\nPRAGMA table_info(inventory_count)')
for r in cur.execute("PRAGMA table_info(inventory_count)"):
    print(r)
print('\nSample deposits:', cur.execute('SELECT * FROM deposits LIMIT 5').fetchall())
print('Sample racks:', cur.execute('SELECT * FROM racks LIMIT 5').fetchall())
print('Sample inventory_count (id, deposit_id, rack_id, location):', cur.execute('SELECT id, deposit_id, rack_id, location FROM inventory_count LIMIT 5').fetchall())
conn.close()
