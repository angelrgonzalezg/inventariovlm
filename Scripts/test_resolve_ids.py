import sqlite3
import sys
from pathlib import Path
# ensure repo root is on sys.path so imports like `db_utils` work when running from scripts/
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from db_utils import get_deposits, get_racks

DB_NAME='inventariovlm.db'

def resolve(deposit_name, rack_name):
    deposits_list = get_deposits()
    racks_list = []
    deposit_id = None
    rack_id = None
    dep_name_norm = deposit_name.strip() if isinstance(deposit_name, str) else deposit_name
    rack_name_norm = rack_name.strip() if isinstance(rack_name, str) else rack_name

    for d in deposits_list:
        try:
            if isinstance(d, (list, tuple)):
                if len(d) >= 2 and str(d[1]).strip() == str(dep_name_norm):
                    deposit_id = d[0]
                    break
                if len(d) >= 3 and str(d[2]).strip() == str(dep_name_norm):
                    deposit_id = d[0]
                    break
                if str(d[0]).strip() == str(dep_name_norm):
                    deposit_id = d[0]
                    break
            else:
                if str(d).strip() == str(dep_name_norm):
                    deposit_id = None
                    break
        except Exception:
            continue

    if deposit_id is not None:
        racks_list = get_racks()(deposit_id)

    for r in racks_list:
        try:
            if isinstance(r, (list, tuple)) and len(r) > 1:
                if str(r[1]).strip() == str(rack_name_norm):
                    rack_id = r[0]
                    break
                if str(r[0]).strip() == str(rack_name_norm):
                    rack_id = r[0]
                    break
            else:
                if str(r).strip() == str(rack_name_norm):
                    rack_id = r
                    break
        except Exception:
            continue

    if deposit_id is None:
        try:
            cur2 = sqlite3.connect(DB_NAME).cursor()
            cur2.execute("SELECT deposit_id FROM deposits WHERE deposit_description = ? COLLATE NOCASE LIMIT 1", (dep_name_norm,))
            rr = cur2.fetchone()
            if rr:
                deposit_id = rr[0]
            else:
                cur2.execute("SELECT deposit_id FROM deposits WHERE deposit_number = ? LIMIT 1", (dep_name_norm,))
                rr = cur2.fetchone()
                if rr:
                    deposit_id = rr[0]
            try:
                cur2.connection.close()
            except Exception:
                pass
        except Exception:
            deposit_id = None

    if rack_id is None:
        try:
            cur3 = sqlite3.connect(DB_NAME).cursor()
            if deposit_id is not None:
                cur3.execute("SELECT rack_id FROM racks WHERE rack_description = ? AND deposit_id = ? COLLATE NOCASE LIMIT 1", (rack_name_norm, deposit_id))
                rr = cur3.fetchone()
                if rr:
                    rack_id = rr[0]
            if rack_id is None:
                cur3.execute("SELECT rack_id FROM racks WHERE rack_description = ? COLLATE NOCASE LIMIT 1", (rack_name_norm,))
                rr = cur3.fetchone()
                if rr:
                    rack_id = rr[0]
            try:
                cur3.connection.close()
            except Exception:
                pass
        except Exception:
            rack_id = None

    return deposit_id, rack_id

if __name__ == '__main__':
    deps = get_deposits()
    print('Deposits (sample):', deps[:5])
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    rows = cur.execute('SELECT id, deposit_id, rack_id, code_item FROM inventory_count LIMIT 20').fetchall()
    print('\nTesting resolution on inventory_count sample rows:')
    for r in rows:
        row_id, dep_id, rack_id, code = r
        dep_desc = ''
        rack_desc = ''
        if dep_id is not None:
            rr = cur.execute('SELECT deposit_description FROM deposits WHERE deposit_id = ?', (dep_id,)).fetchone()
            if rr:
                dep_desc = rr[0]
        if rack_id is not None:
            rr = cur.execute('SELECT rack_description FROM racks WHERE rack_id = ?', (rack_id,)).fetchone()
            if rr:
                rack_desc = rr[0]
        resolved = resolve(dep_desc, rack_desc)
        print(f'row id={row_id} code={code} stored dep_id={dep_id} dep_desc="{dep_desc}" stored rack_id={rack_id} rack_desc="{rack_desc}" -> resolved {resolved}')
    conn.close()
