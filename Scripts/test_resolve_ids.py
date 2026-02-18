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
    if deps:
        first_dep_name = deps[0][1] if isinstance(deps[0], (list,tuple)) and len(deps[0])>1 else deps[0]
        dep_id = deps[0][0] if isinstance(deps[0], (list,tuple)) else None
        racks = get_racks()(dep_id) if dep_id is not None else []
        print('Racks for first deposit:', racks[:5])
        if racks:
            first_rack_name = racks[0][1] if isinstance(racks[0], (list,tuple)) and len(racks[0])>1 else racks[0]
        else:
            first_rack_name = ''
        resolved = resolve(first_dep_name, first_rack_name)
        print(f"Resolve('{first_dep_name}','{first_rack_name}') -> {resolved}")
    else:
        print('No deposits found')
