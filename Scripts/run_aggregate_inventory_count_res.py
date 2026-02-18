import sqlite3
import os
import csv
from datetime import datetime

DB = os.path.join(os.getcwd(), 'inventariovlm.db')
print('Using DB:', DB)
if not os.path.exists(DB):
    raise SystemExit('Database not found')

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Backup current inventory_count_res to CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join(os.getcwd(), 'backups')
os.makedirs(backup_dir, exist_ok=True)
backup_path = os.path.join(backup_dir, f'inventory_count_res_backup_{ts}.csv')
try:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_count_res'")
    if cur.fetchone():
        rows = cur.execute('SELECT * FROM inventory_count_res').fetchall()
        cols = [d[0] for d in cur.description]
        with open(backup_path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            w.writerows(rows)
        print('Backup written to', backup_path)
    else:
        print('No existing inventory_count_res table; nothing to backup')
except Exception as e:
    print('Warning: could not backup inventory_count_res:', e)

# Ensure table exists and columns
cur.execute('''
CREATE TABLE IF NOT EXISTS inventory_count_res (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_item TEXT(10) NOT NULL,
    description_item TEXT,
    boxqty INTEGER DEFAULT 0,
    boxunitqty INTEGER DEFAULT 0,
    boxunittotal INTEGER DEFAULT 0,
    magazijn INTEGER DEFAULT 0,
    winkel INTEGER DEFAULT 0,
    total INTEGER,
    current_inventory INTEGER,
    difference INTEGER,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# Ensure columns sales_qty and purchasing_qty
cur.execute("PRAGMA table_info(inventory_count_res)")
cols_info = cur.fetchall()
cols = [c[1] for c in cols_info]
if 'sales_qty' not in cols:
    cur.execute("ALTER TABLE inventory_count_res ADD COLUMN sales_qty INTEGER DEFAULT 0")
if 'purchasing_qty' not in cols:
    cur.execute("ALTER TABLE inventory_count_res ADD COLUMN purchasing_qty INTEGER DEFAULT 0")
conn.commit()

# Clear existing rows (we choose to replace current summary)
cur.execute('DELETE FROM inventory_count_res')
conn.commit()
print('Cleared inventory_count_res')

# Perform aggregation (assumes sales and purchasing tables with (code_item, qty))
agg_sql = '''
SELECT ic.code_item AS code_item,
       COALESCE(SUM(ic.boxqty),0) AS boxqty,
       COALESCE(SUM(ic.boxunitqty),0) AS boxunitqty,
       COALESCE(SUM(ic.boxunittotal),0) AS boxunittotal,
       COALESCE(SUM(ic.magazijn),0) AS magazijn,
       COALESCE(SUM(ic.winkel),0) AS winkel,
       COALESCE(SUM(ic.total),0) AS total,
       MAX(COALESCE(i.description_item, '')) AS description_item,
       MAX(COALESCE(i.current_inventory,0)) AS current_inventory,
       COALESCE(s.sales_qty, 0) AS sales_qty,
       COALESCE(p.purchasing_qty, 0) AS purchasing_qty
  FROM inventory_count ic
  LEFT JOIN items i ON i.code_item = ic.code_item
  LEFT JOIN (
      SELECT code_item, SUM(sales_qty) AS sales_qty FROM sales GROUP BY code_item
  ) s ON s.code_item = ic.code_item
  LEFT JOIN (
      SELECT code_item, SUM(purchasing_qty) AS purchasing_qty FROM purchasing GROUP BY code_item
  ) p ON p.code_item = ic.code_item
 GROUP BY ic.code_item
'''

try:
    cur.execute(agg_sql)
    rows = cur.fetchall()
    print('Aggregated rows:', len(rows))
    inserted = 0
    ts_now = datetime.now().isoformat()
    for r in rows:
        code_item = r[0] or ''
        boxqty = int(r[1] or 0)
        boxunitqty = int(r[2] or 0)
        boxunittotal = int(r[3] or 0)
        magazijn = int(r[4] or 0)
        winkel = int(r[5] or 0)
        total = int(r[6] or 0)
        description_item = r[7] or ''
        current_inventory = int(r[8] or 0)
        sales_qty = int(r[9] or 0)
        purchasing_qty = int(r[10] or 0)
        total_calc = total + purchasing_qty - sales_qty
        difference = current_inventory - total_calc
        # include total_calc column if present
        cur.execute("PRAGMA table_info(inventory_count_res)")
        cols = [c[1] for c in cur.fetchall()]
        if 'total_calc' in cols:
            cur.execute('''INSERT INTO inventory_count_res
                (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, total_calc, updated_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, total_calc, ts_now)
            )
        else:
            cur.execute('''INSERT INTO inventory_count_res
                (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, updated_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, ts_now)
            )
        inserted += 1
    conn.commit()
    print('Inserted', inserted, 'rows into inventory_count_res')
    # show sample
    cur.execute('SELECT id, code_item, total, current_inventory, difference, sales_qty, purchasing_qty FROM inventory_count_res ORDER BY abs(difference) DESC LIMIT 10')
    sample = cur.fetchall()
    print('\nTop 10 by abs(difference):')
    for s in sample:
        print(s)
except Exception as e:
    print('Error during aggregation:', e)
finally:
    conn.close()

print('Done')
