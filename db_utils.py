import sqlite3

DB_NAME = 'inventariovlm.db'

def obtener_deposits(db_name=DB_NAME):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM deposits")
    deposits = [row[0] for row in cur.fetchall()]
    conn.close()
    return deposits

def obtener_racks(deposit_nombre, db_name=DB_NAME):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("SELECT id FROM deposits WHERE nombre = ?", (deposit_nombre,))
    deposit_id = cur.fetchone()
    racks = []
    if deposit_id:
        cur.execute("SELECT nombre FROM racks WHERE deposit_id = ?", (deposit_id[0],))
        racks = [row[0] for row in cur.fetchall()]
    conn.close()
    return racks

def get_deposits(db_name=DB_NAME):
    try:
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute("SELECT deposit_id, deposit_description FROM deposits ORDER BY deposit_description")
        deposits = cur.fetchall()
        conn.close()
        return deposits
    except Exception:
        return []

def get_racks(db_name=DB_NAME):
    def inner(deposit_id=None):
        try:
            conn = sqlite3.connect(db_name)
            cur = conn.cursor()
            if deposit_id is not None:
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE deposit_id = ? ORDER BY rack_id", (deposit_id,))
            else:
                cur.execute("SELECT rack_id, rack_description FROM racks ORDER BY rack_id")
            racks = cur.fetchall()
            conn.close()
            return racks
        except Exception:
            return []
    return inner
