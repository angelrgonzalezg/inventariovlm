import sqlite3
DB='inventariovlm.db'
conn=sqlite3.connect(DB)
cur=conn.cursor()
try:
    cur.execute("SELECT c.id, c.counter_name, c.count_date, c.deposit_id, c.rack_id, c.location, c.code_item, c.boxqty, c.boxunitqty, c.boxunittotal, c.magazijn, c.winkel, c.total, c.current_inventory, c.difference FROM inventory_count c ORDER BY code_item LIMIT 5")
    rows=cur.fetchall()
    print('Returned rows:', len(rows))
    for r in rows:
        print(r)
except Exception as e:
    print('Error:', e)
finally:
    conn.close()
