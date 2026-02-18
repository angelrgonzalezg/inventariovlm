import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from db_utils import get_deposits, get_racks
from ui_registros import mostrar_registros, mostrar_registros_resumen
import pandas as pd
from datetime import datetime
import sys
import os
import sqlite3
import sys
import os

# Resolve database path so the frozen executable finds the DB next to the exe.
if getattr(sys, "frozen", False):
    # Running in a PyInstaller bundle
    _base_dir = os.path.dirname(sys.executable)
else:
    # Running in normal Python environment
    _base_dir = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(_base_dir, 'inventariovlm.db')
def main():

    def importar_inventory():
        file_path = filedialog.askopenfilename(
            title="Selecciona archivo de inventario",
            filetypes=[("CSV Files", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"No se encontró el archivo: {file_path}")
            return
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        # Normalizar nombres de columnas
        df = df.rename(columns={
            'codeitem': 'code_item',
            'remark': 'remarks',
            'remarks': 'remarks',
            'boxqty': 'boxqty',
            'boxunitqty': 'boxunitqty',
            'boxunittotal': 'boxunittotal',
            'magazijn': 'magazijn',
            'winkel': 'winkel',
            'total': 'total',
            'counter_name': 'counter_name',
            'deposit_id': 'deposit_id',
            'rack_id': 'rack_id',
            'count_date': 'count_date',
        })
        # Conversión de tipos y valores
        for col in ['boxqty', 'boxunitqty', 'boxunittotal', 'magazijn', 'winkel', 'total', 'deposit_id', 'rack_id']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].replace('', 0), errors='coerce').fillna(0).astype(int)

        # Formatear fecha a ISO (intenta varios formatos; usa hoy si no puede parsear)
        if 'count_date' in df.columns:
            df['count_date'] = pd.to_datetime(df['count_date'], dayfirst=True, errors='coerce').dt.date
            df['count_date'] = df['count_date'].apply(lambda d: d.isoformat() if pd.notna(d) else datetime.now().date().isoformat())
        else:
            df['count_date'] = datetime.now().date().isoformat()

        # Insertar en la base de datos
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        insertados = 0
        failures = []
        # helper: resolve deposit and rack values
        def resolve_deposit(value):
            """Return (deposit_id, deposit_description) or (None, None) if not found."""
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return (None, None)
            # try numeric id
            try:
                vid = int(str(value))
                cur.execute("SELECT deposit_id, deposit_description FROM deposits WHERE deposit_id = ?", (vid,))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            # try by description (case-insensitive)
            try:
                cur.execute("SELECT deposit_id, deposit_description FROM deposits WHERE lower(deposit_description)=lower(?)", (str(value).strip(),))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            # try partial match
            try:
                cur.execute("SELECT deposit_id, deposit_description FROM deposits WHERE deposit_description LIKE ?", (f"%{str(value).strip()}%",))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            return (None, None)

        def resolve_rack(value, deposit_id=None):
            """Return (rack_id, rack_description) or (None, None) if not found."""
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return (None, None)
            # try numeric id
            try:
                vid = int(str(value))
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE rack_id = ?", (vid,))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            # try by description with deposit context
            try:
                if deposit_id:
                    cur.execute("SELECT rack_id, rack_description FROM racks WHERE deposit_id = ? AND lower(rack_description)=lower(?)", (deposit_id, str(value).strip()))
                    r = cur.fetchone()
                    if r:
                        return (r[0], r[1] or '')
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE lower(rack_description)=lower(?)", (str(value).strip(),))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            # try partial match
            try:
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE rack_description LIKE ?", (f"%{str(value).strip()}%",))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            return (None, None)

        for idx, row in df.iterrows():
                # Always insert new records even if duplicates exist (allow multiple records)
                # Previous behavior prompted the user when a code_item already existed; that prompt
                # was removed per request so imports do not block for user input.
                # Resolve deposit and rack values from CSV fields; accept deposit_id/ deposit / deposit_description
                raw_dep = None
                raw_rack = None
                for key in ('deposit_id', 'deposit', 'deposit_description', 'deposito'):
                    if key in df.columns and row.get(key, '') not in (None, ''):
                        raw_dep = row.get(key)
                        break
                for key in ('rack_id', 'rack', 'rack_description'):
                    if key in df.columns and row.get(key, '') not in (None, ''):
                        raw_rack = row.get(key)
                        break

                dep_id_resolved = None
                dep_desc_resolved = ''
                if raw_dep is not None:
                    dep_id_resolved, dep_desc_resolved = resolve_deposit(raw_dep)
                    if dep_id_resolved is None:
                        # cannot resolve deposit -> treat as failure
                        try:
                            row_dict = row.to_dict()
                        except Exception:
                            row_dict = {"code_item": row.get('code_item', '')}
                        row_dict['_error'] = f"Deposit not found: {raw_dep}"
                        row_dict['_row_index'] = int(idx) if idx is not None else None
                        failures.append(row_dict)
                        continue

                rack_id_resolved = None
                rack_desc_resolved = ''
                if raw_rack is not None:
                    rack_id_resolved, rack_desc_resolved = resolve_rack(raw_rack, dep_id_resolved)
                    if rack_id_resolved is None:
                        try:
                            row_dict = row.to_dict()
                        except Exception:
                            row_dict = {"code_item": row.get('code_item', '')}
                        row_dict['_error'] = f"Rack not found: {raw_rack}"
                        row_dict['_row_index'] = int(idx) if idx is not None else None
                        failures.append(row_dict)
                        continue

                # Compute location
                location = ''
                if dep_desc_resolved and rack_desc_resolved:
                    location = f"{dep_desc_resolved} - {rack_desc_resolved}"
                elif dep_desc_resolved:
                    location = dep_desc_resolved
                elif rack_desc_resolved:
                    location = rack_desc_resolved

                # Prepare values for insert: prefer explicit deposit_id/rack_id columns if provided and resolved, else 0
                deposit_id_val = dep_id_resolved or 0
                rack_id_val = rack_id_resolved or 0

                # Try to insert row; on error record failure and continue
                try:
                    cur.execute("""
                        INSERT INTO inventory_count
                        (counter_name, code_item, magazijn, winkel, total, remarks, current_inventory, difference, count_date, location, deposit_id, rack_id, boxqty, boxunitqty, boxunittotal)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get('counter_name', ''),
                        row.get('code_item', ''),
                        row.get('magazijn', 0),
                        row.get('winkel', 0),
                        row.get('total', 0),
                        row.get('remarks', ''),
                        row.get('current_inventory', 0) if 'current_inventory' in df.columns else 0,
                        row.get('difference', row.get('total', 0)),
                        row.get('count_date', datetime.now().date().isoformat()),
                        location,
                        deposit_id_val,
                        rack_id_val,
                        row.get('boxqty', 0),
                        row.get('boxunitqty', 0),
                        row.get('boxunittotal', 0)
                    ))
                    insertados += 1
                except Exception as e:
                    # Record failure: include original row data and error message
                    try:
                        row_dict = row.to_dict()
                    except Exception:
                        row_dict = {"code_item": row.get('code_item', '' )}
                    row_dict['_error'] = str(e)
                    row_dict['_row_index'] = int(idx) if idx is not None else None
                    failures.append(row_dict)
                    # continue with next row
                    continue
        conn.commit()
        conn.close()

        # If there were failures, write them to a CSV log in backups/
        if failures:
            backup_dir = os.path.join(os.getcwd(), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fail_path = os.path.join(backup_dir, f"import_errors_{ts}.csv")
            try:
                import csv as _csv
                # Write header as union of keys
                keys = set()
                for r in failures:
                    keys.update(r.keys())
                keys = list(keys)
                with open(fail_path, 'w', encoding='utf-8', newline='') as fh:
                    writer = _csv.DictWriter(fh, fieldnames=keys)
                    writer.writeheader()
                    for r in failures:
                        writer.writerow(r)
            except Exception as e:
                print(f"No se pudo escribir el log de importación: {e}")

        msg = f"Importación completada. Registros insertados: {insertados}."
        if failures:
            msg += f" Fallos: {len(failures)}. Log: {fail_path}"
        messagebox.showinfo("Importación completada", msg)

    def importar_consolidado_csv():
        """Import a CSV with the same structure and insert all rows into `consolidado_csv`.

        This importer will not check whether the `code_item` exists in `items`.
        It will attempt to resolve deposit/rack descriptions to ids (best-effort);
        if they cannot be resolved the row is still inserted with deposit_id=0, rack_id=0 and empty location.
        """
        file_path = filedialog.askopenfilename(
            title="Selecciona archivo consolidado",
            filetypes=[("CSV Files", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"No se encontró el archivo: {file_path}")
            return
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        # Normalize column names (same mapping as the main importer)
        df = df.rename(columns={
            'codeitem': 'code_item',
            'remark': 'remarks',
            'remarks': 'remarks',
            'boxqty': 'boxqty',
            'boxunitqty': 'boxunitqty',
            'boxunittotal': 'boxunittotal',
            'magazijn': 'magazijn',
            'winkel': 'winkel',
            'total': 'total',
            'counter_name': 'counter_name',
            'deposit_id': 'deposit_id',
            'rack_id': 'rack_id',
            'count_date': 'count_date',
        })
        for col in ['boxqty', 'boxunitqty', 'boxunittotal', 'magazijn', 'winkel', 'total', 'deposit_id', 'rack_id']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].replace('', 0), errors='coerce').fillna(0).astype(int)

        if 'count_date' in df.columns:
            df['count_date'] = pd.to_datetime(df['count_date'], dayfirst=True, errors='coerce').dt.date
            df['count_date'] = df['count_date'].apply(lambda d: d.isoformat() if pd.notna(d) else datetime.now().date().isoformat())
        else:
            df['count_date'] = datetime.now().date().isoformat()

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        # Ensure consolidado_csv table exists (basic schema similar to inventory_count)
        try:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS consolidado_csv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    counter_name TEXT,
                    code_item TEXT,
                    magazijn INTEGER,
                    winkel INTEGER,
                    total INTEGER,
                    remarks TEXT,
                    current_inventory INTEGER,
                    difference INTEGER,
                    count_date TEXT,
                    location TEXT,
                    deposit_id INTEGER,
                    rack_id INTEGER,
                    boxqty INTEGER,
                    boxunitqty INTEGER,
                    boxunittotal INTEGER
                )
            ''')
        except Exception:
            # ignore if creation fails for some reason
            pass

        insertados = 0
        failures = []

        def resolve_deposit(value):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return (None, None)
            try:
                vid = int(str(value))
                cur.execute("SELECT deposit_id, deposit_description FROM deposits WHERE deposit_id = ?", (vid,))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            try:
                cur.execute("SELECT deposit_id, deposit_description FROM deposits WHERE lower(deposit_description)=lower(?)", (str(value).strip(),))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            try:
                cur.execute("SELECT deposit_id, deposit_description FROM deposits WHERE deposit_description LIKE ?", (f"%{str(value).strip()}%",))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            return (None, None)

        def resolve_rack(value, deposit_id=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return (None, None)
            try:
                vid = int(str(value))
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE rack_id = ?", (vid,))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            try:
                if deposit_id:
                    cur.execute("SELECT rack_id, rack_description FROM racks WHERE deposit_id = ? AND lower(rack_description)=lower(?)", (deposit_id, str(value).strip()))
                    r = cur.fetchone()
                    if r:
                        return (r[0], r[1] or '')
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE lower(rack_description)=lower(?)", (str(value).strip(),))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            try:
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE rack_description LIKE ?", (f"%{str(value).strip()}%",))
                r = cur.fetchone()
                if r:
                    return (r[0], r[1] or '')
            except Exception:
                pass
            return (None, None)

        for idx, row in df.iterrows():
            # Resolve deposit/rack if present, but do not abort on failure; insert anyway with defaults
            raw_dep = None
            raw_rack = None
            for key in ('deposit_id', 'deposit', 'deposit_description', 'deposito'):
                if key in df.columns and row.get(key, '') not in (None, ''):
                    raw_dep = row.get(key)
                    break
            for key in ('rack_id', 'rack', 'rack_description'):
                if key in df.columns and row.get(key, '') not in (None, ''):
                    raw_rack = row.get(key)
                    break

            dep_id_resolved = None
            dep_desc_resolved = ''
            if raw_dep is not None:
                dep_id_resolved, dep_desc_resolved = resolve_deposit(raw_dep)

            rack_id_resolved = None
            rack_desc_resolved = ''
            if raw_rack is not None:
                rack_id_resolved, rack_desc_resolved = resolve_rack(raw_rack, dep_id_resolved)

            location = ''
            if dep_desc_resolved and rack_desc_resolved:
                location = f"{dep_desc_resolved} - {rack_desc_resolved}"
            elif dep_desc_resolved:
                location = dep_desc_resolved
            elif rack_desc_resolved:
                location = rack_desc_resolved

            deposit_id_val = dep_id_resolved or 0
            rack_id_val = rack_id_resolved or 0

            try:
                cur.execute('''
                    INSERT INTO consolidado_csv
                    (counter_name, code_item, magazijn, winkel, total, remarks, current_inventory, difference, count_date, location, deposit_id, rack_id, boxqty, boxunitqty, boxunittotal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('counter_name', ''),
                    row.get('code_item', ''),
                    row.get('magazijn', 0),
                    row.get('winkel', 0),
                    row.get('total', 0),
                    row.get('remarks', ''),
                    row.get('current_inventory', 0) if 'current_inventory' in df.columns else 0,
                    row.get('difference', row.get('total', 0)),
                    row.get('count_date', datetime.now().date().isoformat()),
                    location,
                    deposit_id_val,
                    rack_id_val,
                    row.get('boxqty', 0),
                    row.get('boxunitqty', 0),
                    row.get('boxunittotal', 0)
                ))
                insertados += 1
            except Exception as e:
                try:
                    row_dict = row.to_dict()
                except Exception:
                    row_dict = {"code_item": row.get('code_item', '')}
                row_dict['_error'] = str(e)
                row_dict['_row_index'] = int(idx) if idx is not None else None
                failures.append(row_dict)
                continue

        conn.commit()
        conn.close()

        if failures:
            backup_dir = os.path.join(os.getcwd(), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fail_path = os.path.join(backup_dir, f"consolidado_import_errors_{ts}.csv")
            try:
                import csv as _csv
                keys = set()
                for r in failures:
                    keys.update(r.keys())
                keys = list(keys)
                with open(fail_path, 'w', encoding='utf-8', newline='') as fh:
                    writer = _csv.DictWriter(fh, fieldnames=keys)
                    writer.writeheader()
                    for r in failures:
                        writer.writerow(r)
            except Exception as e:
                print(f"No se pudo escribir el log de importación consolidado: {e}")

        msg = f"Importación consolidado completada. Registros insertados: {insertados}."
        if failures:
            msg += f" Fallos: {len(failures)}. Log: {fail_path}"
        messagebox.showinfo("Importación consolidado completada", msg)

    # ...widgets...
    # (los binds van después de crear los widgets, sin indentación extra)
    root = tk.Tk()
    root.title("VLM Inventary")
    root.geometry("640x420")

    # --- Widgets principales ---
    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="both", expand=True)

    btn_importar_inventory = ttk.Button(frm, text="Importar Inventory", command=importar_inventory)
    btn_importar_inventory.grid(row=22, column=0, pady=8)
    btn_importar_consolidado = ttk.Button(frm, text="Importar Consolidado CSV", command=importar_consolidado_csv)
    btn_importar_consolidado.grid(row=23, column=0, pady=8)

    # Campo Remark después de Winkel
    ttk.Label(frm, text="Comentario:").grid(row=11, column=0, sticky="e")
    entry_remark = ttk.Entry(frm, width=36)
    entry_remark.grid(row=11, column=1, columnspan=2, sticky="w", padx=2)
    # Nombre del contador
    ttk.Label(frm, text="Contador:").grid(row=0, column=0, sticky="e")
    combo_name = ttk.Combobox(frm, values=["LUZMERY", "MALINA", "VICTORIA"], width=18)
    combo_name.grid(row=0, column=1, sticky="w")


    # Fecha
    ttk.Label(frm, text="Fecha:").grid(row=1, column=0, sticky="e")
    date_entry = DateEntry(frm, width=12)
    date_entry.grid(row=1, column=1, sticky="w")

    # Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    racks_list = get_racks()()  # Llama get_racks() para obtener inner, luego inner() para la lista
    racks_display = [r[1] for r in racks_list] if racks_list and len(racks_list[0]) > 1 else [r[0] for r in racks_list]
    # Si la descripción sigue vacía, usar rack_code
    if all(not val for val in racks_display):
        racks_display = [r[0] for r in racks_list]
    ttk.Label(frm, text="Deposit:").grid(row=2, column=0, sticky="e")
    combo_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    combo_deposit.grid(row=2, column=1, sticky="w")
    ttk.Label(frm, text="Rack:").grid(row=3, column=0, sticky="e")
    combo_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    combo_rack.grid(row=3, column=1, sticky="w")

    # Código
    ttk.Label(frm, text="Producto:").grid(row=4, column=0, sticky="e")
    entry_code = ttk.Entry(frm, width=18)
    entry_code.grid(row=4, column=1, sticky="w")

    # Descripción
    ttk.Label(frm, text="Descripción:").grid(row=5, column=0, sticky="e")
    entry_desc = ttk.Entry(frm, width=36, state="readonly")
    entry_desc.grid(row=5, column=1, sticky="w")


    # Cajas y BoxUnitqty
    ttk.Label(frm, text="Cajas:").grid(row=6, column=0, sticky="e")
    entry_boxqty = ttk.Entry(frm, width=8)
    entry_boxqty.grid(row=6, column=1, sticky="w")
    entry_boxqty.insert(0, "0")

    ttk.Label(frm, text="Unidades por caja:").grid(row=7, column=0, sticky="e")
    entry_boxunitqty = ttk.Entry(frm, width=8)
    entry_boxunitqty.grid(row=7, column=1, sticky="w")
    entry_boxunitqty.insert(0, "0")

    ttk.Label(frm, text="Total en cajas:").grid(row=8, column=0, sticky="e")
    entry_boxunittotal = ttk.Entry(frm, width=10, state="readonly")
    entry_boxunittotal.grid(row=8, column=1, sticky="w")
    entry_boxunittotal.insert(0, "0")

    # Magazijn y Winkel
    ttk.Label(frm, text="Sueltos:").grid(row=9, column=0, sticky="e")
    entry_mag = ttk.Entry(frm, width=8)
    entry_mag.grid(row=9, column=1, sticky="w")
    entry_mag.insert(0, "0")

    ttk.Label(frm, text="Tienda:").grid(row=10, column=0, sticky="e")
    entry_win = ttk.Entry(frm, width=8)
    entry_win.grid(row=10, column=1, sticky="w")
    entry_win.insert(0, "0")

    def on_boxqty_enter(event=None):
        entry_boxunitqty.focus_set()
        entry_boxunitqty.selection_range(0, tk.END)

    def on_boxunitqty_enter(event=None):
        entry_mag.focus_set()
        entry_mag.selection_range(0, tk.END)

    def on_magazijn_enter(event=None):
        entry_win.focus_set()
        entry_win.selection_range(0, tk.END)

    def on_winkel_enter(event=None):
        btn_guardar.focus_set()
        if isinstance(btn_guardar, ttk.Entry):
            btn_guardar.selection_range(0, tk.END)

    entry_boxqty.bind("<Return>", on_boxqty_enter)
    entry_boxunitqty.bind("<Return>", on_boxunitqty_enter)
    entry_mag.bind("<Return>", on_magazijn_enter)
    entry_win.bind("<Return>", on_winkel_enter)

    def on_deposit_change(event=None):
        # Ya no se actualiza racks por depósito, racks es independiente
        pass
    combo_deposit.bind("<<ComboboxSelected>>", on_deposit_change)

    combo_deposit.bind("<<ComboboxSelected>>", on_deposit_change)

    # Location label

    lbl_location = ttk.Label(frm, text="")
    lbl_location.grid(row=11, column=1, sticky="w")

    # Inventario actual
    lbl_current = ttk.Label(frm, text="Inventario actual: ")
    lbl_current.grid(row=12, column=0, sticky="w")
    def update_boxunittotal(*args):
        try:
            boxqty = int(entry_boxqty.get())
            boxunitqty = int(entry_boxunitqty.get())
            total = boxqty * boxunitqty
        except Exception:
            total = 0
        entry_boxunittotal.config(state="normal")
        entry_boxunittotal.delete(0, tk.END)
        entry_boxunittotal.insert(0, str(total))
        entry_boxunittotal.config(state="readonly")

    entry_boxqty.bind("<KeyRelease>", update_boxunittotal)
    entry_boxunitqty.bind("<KeyRelease>", update_boxunittotal)

    # --- Botones ---
    btn_export = ttk.Button(frm, text="Exportar", command=lambda: export_data())
    btn_export.grid(row=20, column=0, pady=8)
    btn_guardar = ttk.Button(frm, text="Guardar", command=lambda: guardar())
    btn_guardar.grid(row=20, column=1, pady=8)
    btn_import = ttk.Button(frm, text="Importar Catálogo", command=lambda: import_catalog())
    btn_import.grid(row=21, column=0, pady=8)
    btn_buscar = ttk.Button(frm, text="Buscar", command=lambda: buscar_item())
    btn_buscar.grid(row=21, column=1, pady=8)
    # Botón para actualizar 'current_inventory' en la tabla 'items' desde un CSV
    def actualizar_current_inventory_from_csv(file_path=None):
        # Prompt for file if not provided
        if not file_path:
            file_path = filedialog.askopenfilename(title="Selecciona CSV para actualizar current_inventory",
                                                   filetypes=[("CSV Files", "*.csv"), ("All files", "*")],
                                                   parent=root)
            if not file_path:
                return
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"No se encontró el archivo: {file_path}", parent=root)
            return
        try:
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el CSV: {e}", parent=root)
            return
        # Normalize column name variations
        col_map = {"code": "code_item", "codigo": "code_item", "number": "code_item", "current": "current_inventory", "inventory": "current_inventory"}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        if "code_item" not in df.columns and "code" not in df.columns:
            messagebox.showerror("Error", "El CSV debe contener la columna 'code_item' (o 'code'/'number')", parent=root)
            return
        if "current_inventory" not in df.columns:
            messagebox.showerror("Error", "El CSV debe contener la columna 'current_inventory' (o 'current'/'inventory')", parent=root)
            return
        # Clean and convert
        df["code_item"] = df["code_item"].astype(str).str.strip()
        df["current_inventory"] = pd.to_numeric(df["current_inventory"].replace("", "0"), errors="coerce").fillna(0).astype(int)

        # Ensure backups directory exists and back up 'items' table before changes
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        conn = sqlite3.connect(DB_NAME)
        try:
            try:
                df_items_backup = pd.read_sql_query("SELECT * FROM items", conn)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"items_backup_{ts}.csv")
                df_items_backup.to_csv(backup_path, index=False)
            except Exception:
                # If backup fails, continue but warn in console
                print("Advertencia: no se pudo crear respaldo de 'items' antes de la actualización")

            cur = conn.cursor()
            updated = 0
            not_found = []
            for _, row in df.iterrows():
                code = str(row["code_item"]).strip()
                val = int(row["current_inventory"])
                cur.execute("SELECT 1 FROM items WHERE code_item = ?", (code,))
                if cur.fetchone():
                    cur.execute("UPDATE items SET current_inventory = ? WHERE code_item = ?", (val, code))
                    updated += 1
                    continue
                alt = code.lstrip("0")
                if alt:
                    cur.execute("SELECT 1 FROM items WHERE code_item = ?", (alt,))
                    if cur.fetchone():
                        cur.execute("UPDATE items SET current_inventory = ? WHERE code_item = ?", (val, alt))
                        updated += 1
                        continue
                not_found.append(code)
            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Error al actualizar la base de datos: {e}", parent=root)
            conn.close()
            return
        conn.close()

        # Save not_found list to backups for review
        ts2 = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not_found:
            nf_path = os.path.join(backup_dir, f"not_found_current_inventory_{ts2}.txt")
            try:
                with open(nf_path, "w", encoding="utf-8") as f:
                    for c in not_found:
                        f.write(f"{c}\n")
            except Exception:
                print("Advertencia: no se pudo escribir la lista de códigos no encontrados en backups")

        summary = f"Registros actualizados: {updated}"
        if not_found:
            summary += f"\nCódigos no encontrados: {len(not_found)} (guardados en {nf_path})"
        messagebox.showinfo("Actualización completada", summary, parent=root)

    btn_update_current = ttk.Button(frm, text="Actualizar current_inventory (CSV)", command=lambda: actualizar_current_inventory_from_csv())
    btn_update_current.grid(row=24, column=0, pady=8)

    def generar_inventory_count_res():
        """Aggregate `inventory_count` by `code_item` and insert summarized rows into `inventory_count_res`.
        This function is compatible with the existing table schema (columns: code_item, description_item,
        boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, updated_date).
        The user is asked whether to clear existing rows before inserting.
        """
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            # Ensure table exists with expected schema (if missing, create compatible schema)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS inventory_count_res (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_item TEXT(10) NOT NULL REFERENCES items (code_item),
                    description_item TEXT,
                    boxqty INTEGER DEFAULT 0,
                    boxunitqty INTEGER DEFAULT 0,
                    boxunittotal INTEGER DEFAULT 0,
                    magazijn INTEGER DEFAULT 0,
                    winkel INTEGER DEFAULT 0,
                    total INTEGER,
                    current_inventory INTEGER,
                    difference INTEGER,
                    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (code_item) REFERENCES items (code_item)
                )
            ''')

            # Ask whether to clear existing data
            clear = messagebox.askyesno("Confirmar", "¿Borrar registros existentes en 'inventory_count_res' antes de generar?\n(Si no, se agregarán nuevas filas)", parent=root)
            if clear:
                cur.execute("DELETE FROM inventory_count_res")

            # Ensure sales_qty and purchasing_qty columns exist in inventory_count_res
            try:
                cur.execute("PRAGMA table_info(inventory_count_res)")
                cols_info = cur.fetchall()
                cols = [c[1] for c in cols_info]
            except Exception:
                cols = []
            if 'sales_qty' not in cols:
                try:
                    cur.execute("ALTER TABLE inventory_count_res ADD COLUMN sales_qty INTEGER DEFAULT 0")
                except Exception:
                    pass
            if 'purchasing_qty' not in cols:
                try:
                    cur.execute("ALTER TABLE inventory_count_res ADD COLUMN purchasing_qty INTEGER DEFAULT 0")
                except Exception:
                    pass
            # Re-query columns to detect if total_calc exists
            try:
                cur.execute("PRAGMA table_info(inventory_count_res)")
                cols_info = cur.fetchall()
                cols = [c[1] for c in cols_info]
            except Exception:
                cols = []
            has_total_calc = 'total_calc' in cols

            # Aggregate values from inventory_count, and also include sales and purchasing sums by code_item
            # sales and purchasing are expected to be tables with at least (code_item, qty)
            cur.execute('''
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
            ''')
            rows = cur.fetchall()
            if not rows:
                messagebox.showinfo("Sin datos", "No se encontraron registros en 'inventory_count' para agregar.", parent=root)
                conn.close()
                return

            inserted = 0
            ts = datetime.now().isoformat()
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
                # compute sales/purchasing and derived total_calc and difference
                sales_qty = int(r[9] or 0)
                purchasing_qty = int(r[10] or 0)
                total_calc = total + purchasing_qty - sales_qty
                difference = current_inventory - total_calc

                if has_total_calc:
                    cur.execute(
                        '''INSERT INTO inventory_count_res
                           (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, total_calc, updated_date)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, total_calc, ts)
                    )
                else:
                    cur.execute(
                        '''INSERT INTO inventory_count_res
                           (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, updated_date)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, sales_qty, purchasing_qty, ts)
                    )
                inserted += 1

            conn.commit()
            conn.close()
            messagebox.showinfo("OK", f"Se insertaron {inserted} registros en inventory_count_res", parent=root)
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            messagebox.showerror("Error", f"Error al generar inventory_count_res: {e}", parent=root)

    btn_gen_res = ttk.Button(frm, text="Generar inventory_count_res", command=generar_inventory_count_res)
    btn_gen_res.grid(row=25, column=0, pady=8)
    msg_guardado = tk.StringVar()
    lbl_guardado = ttk.Label(frm, textvariable=msg_guardado, foreground="green")
    lbl_guardado.grid(row=20, column=2, padx=8, sticky="w")
    btn_registros = ttk.Button(frm, text="Ver Registros", command=lambda: mostrar_registros(root))
    btn_registros.grid(row=22, column=1, pady=8)
    btn_registros_resumen = ttk.Button(frm, text="Ver Registros Resumen", command=lambda: mostrar_registros_resumen(root))
    btn_registros_resumen.grid(row=22, column=2, pady=8, padx=6)

    # Quick reports dropdown (below 'Ver Registros')
    rpt_options = [
        "Reporte por Deposito",
        "Reporte por contador",
        "Reporte Verificacion",
        "Reporte Verificacion (con Remarks)",
        "Reporte Diferencias",
        "Diferencias Resumen (inventory_count_res)",
        "Registros Sin codigo",
        "Items no en Inventario",
        "Diferencias por Items",
        "Diferencias > X",
        "Diferencias por Counter/Loc/Item",
        "Diferencia Item Detalle",
    ]
    cmb_rpt_main = ttk.Combobox(frm, values=rpt_options, state="readonly", width=36)
    cmb_rpt_main.set(rpt_options[0])
    def ejecutar_reporte_main():
        sel = cmb_rpt_main.get().strip()
        if not sel:
            return
        key = sel.lower().replace(" ", "").replace("/", "").replace("\u00a0", "")
        try:
            import ui_pdf_report as rpt
        except Exception as e:
            # If main report module failed to import (syntax error), try the standalone resumen module
            try:
                import ui_pdf_report_resumen as rpt
            except Exception:
                messagebox.showerror("Error", f"No se pudo cargar los reportes: {e}", parent=root)
                return
        try:
            if "deposito" in key and "por" in key:
                rpt.generate_pdf_report_por_deposito(root, db_path=DB_NAME)
            elif "contador" in key and "por" in key:
                rpt.generate_pdf_report_por_contador(root, db_path=DB_NAME)
            elif "verific" in key and "remarks" in key:
                fn = getattr(rpt, 'generate_pdf_report_verificacion_remarks', None)
                if fn is not None:
                    fn(root, db_path=DB_NAME)
                else:
                    try:
                        import ui_pdf_report_resumen as rpt_res
                        rpt_res.generate_pdf_report_verificacion_remarks(root, db_path=DB_NAME)
                    except Exception:
                        raise
            elif "verific" in key:
                rpt.generate_pdf_report_verificacion(root, db_path=DB_NAME)
            elif "diferencias>" in key or "diferencias>x" in key or ">x" in key:
                rpt.generate_pdf_report_diferencias_threshold(root, db_path=DB_NAME)
            elif "counterlocitem" in key or "counterlocitem" in key:
                rpt.generate_pdf_report_diferencias_por_counter(root, db_path=DB_NAME)
            elif "diferenciasporitems" in key or "poritem" in key:
                rpt.generate_pdf_report_diferencias_por_item(root, db_path=DB_NAME)
            elif "sincodigo" in key or "registrossincodigo" in key or "nocode" in key:
                # prefer function on loaded module, otherwise call the resumen module
                fn = getattr(rpt, 'generate_pdf_report_nocode_items', None)
                if fn is not None:
                    fn(root, db_path=DB_NAME)
                else:
                    try:
                        import ui_pdf_report_resumen as rpt_res
                        rpt_res.generate_pdf_report_nocode_items(root, db_path=DB_NAME)
                    except Exception:
                        raise
            elif "itemsnoeninventario" in key or "noeninventario" in key or "itemsno" in key:
                fn = getattr(rpt, 'generate_pdf_report_items_not_in_inventory', None)
                if fn is not None:
                    fn(root, db_path=DB_NAME)
                else:
                    try:
                        import ui_pdf_report_resumen as rpt_res
                        rpt_res.generate_pdf_report_items_not_in_inventory(root, db_path=DB_NAME)
                    except Exception:
                        raise
            elif "resumen" in key or "inventory_count_res" in key:
                # Always use the standalone resumen implementation to ensure it includes the updated columns
                try:
                    import ui_pdf_report_resumen as rpt_res
                    rpt_res.generate_pdf_report_diferencias_resumen(root, db_path=DB_NAME)
                except Exception:
                    # fallback: try the loaded module's implementation if resumen module fails
                    fn = getattr(rpt, "generate_pdf_report_diferencias_resumen", None)
                    if fn is not None:
                        fn(root, db_path=DB_NAME)
                    else:
                        raise
            elif "diferenciaitemdetalle" in key or "itemdetalle" in key:
                rpt.generate_pdf_report_diferencias_item_detalle(root, db_path=DB_NAME)
            elif "diferencias" in key:
                rpt.generate_pdf_report_diferencias(root, db_path=DB_NAME)
            else:
                rpt.generate_pdf_report_diferencias(root, db_path=DB_NAME)
        except Exception as e:
            messagebox.showerror("Error", f"Error al ejecutar el reporte: {e}", parent=root)

    btn_rpt_main = ttk.Button(frm, text="Ejecutar reporte", command=ejecutar_reporte_main)
    cmb_rpt_main.grid(row=23, column=1, padx=6, pady=8, sticky="w")
    btn_rpt_main.grid(row=23, column=2, padx=6, pady=8, sticky="w")

    # Botón para generar reporte PDF (usa ui_pdf_report.add_pdf_report_button)
    # Try to load the main reports module; if it's broken, prefer the small resumen module.
    try:
        import ui_pdf_report as rpt_mod
    except Exception:
        try:
            import ui_pdf_report_resumen as rpt_mod
        except Exception:
            rpt_mod = None

    def _missing_btn_factory(msg="Reporte no disponible"):
        def _create(parent, **kwargs):
            btn = ttk.Button(parent, text=kwargs.get('button_text', 'Reporte'), command=lambda: messagebox.showerror('Error', msg, parent=root))
            return btn
        return _create

    if rpt_mod is None:
        add_pdf_report_button = _missing_btn_factory('No se pudo cargar el módulo de reportes')
        add_pdf_report_por_deposito_button = add_pdf_report_button
        add_pdf_report_por_contador_button = add_pdf_report_button
        add_pdf_report_diferencias_button = add_pdf_report_button
        add_pdf_report_diferencias_por_item_button = add_pdf_report_button
    else:
        add_pdf_report_button = getattr(rpt_mod, 'add_pdf_report_button', None)
        add_pdf_report_por_deposito_button = getattr(rpt_mod, 'add_pdf_report_por_deposito_button', add_pdf_report_button)
        add_pdf_report_por_contador_button = getattr(rpt_mod, 'add_pdf_report_por_contador_button', add_pdf_report_button)
        add_pdf_report_diferencias_button = getattr(rpt_mod, 'add_pdf_report_diferencias_button', add_pdf_report_button)
        add_pdf_report_diferencias_por_item_button = getattr(rpt_mod, 'add_pdf_report_diferencias_por_item_button', add_pdf_report_button)

    try:
        btn_pdf = add_pdf_report_button(frm, db_path=DB_NAME, button_text="Generar PDF")
        try:
            btn_pdf.grid(row=24, column=2, pady=8)
        except Exception:
            pass
    except Exception:
        # If creation fails, create a placeholder that shows an error when clicked
        btn_pdf = ttk.Button(frm, text="Generar PDF", command=lambda: messagebox.showerror('Error', 'Reporte no disponible', parent=root))
        try:
            btn_pdf.grid(row=24, column=2, pady=8)
        except Exception:
            pass

    # Botón para reporte por depósito
    btn_pdf_deposito = add_pdf_report_por_deposito_button(frm, db_path=DB_NAME, button_text="Reporte por Depósito")
    try:
        btn_pdf_deposito.grid(row=25, column=2, pady=8)
    except Exception:
        pass

    # Botón para reporte por contador
    btn_pdf_contador = add_pdf_report_por_contador_button(frm, db_path=DB_NAME, button_text="Reporte por Contador")
    try:
        btn_pdf_contador.grid(row=26, column=2, pady=8)
    except Exception:
        pass

    # Botón reporte de verificación (orden por id)
    try:
        from ui_pdf_report import add_pdf_report_verificacion_button
        btn_pdf_verif = add_pdf_report_verificacion_button(frm, db_path=DB_NAME, button_text="Reporte Verificación")
        try:
            btn_pdf_verif.grid(row=27, column=2, pady=8)
        except Exception:
            pass
    except Exception:
        # if import fails, ignore
        pass

    # Botón reporte Verificación (solo con remarks)
    try:
        try:
            from ui_pdf_report_resumen import add_pdf_report_verificacion_remarks_button as add_pdf_report_verificacion_remarks_button
        except Exception:
            from ui_pdf_report import add_pdf_report_verificacion_remarks_button
        btn_pdf_verif_r = add_pdf_report_verificacion_remarks_button(frm, db_path=DB_NAME, button_text="Verificación (Remarks)")
        try:
            btn_pdf_verif_r.grid(row=27, column=3, pady=8)
        except Exception:
            pass
    except Exception:
        pass

    # Botón reporte de diferencias (por item y ubicación)
    try:
        from ui_pdf_report import add_pdf_report_diferencias_button
        btn_pdf_diff = add_pdf_report_diferencias_button(frm, db_path=DB_NAME, button_text="Reporte Diferencias")
        try:
            btn_pdf_diff.grid(row=28, column=2, pady=8)
        except Exception:
            pass
    except Exception:
        pass

    # Botón reporte Diferencias por Item (agrupa sólo por código)
    try:
        from ui_pdf_report import (
            add_pdf_report_diferencias_por_item_button,
            add_pdf_report_diferencias_threshold_button,
            add_pdf_report_diferencias_por_counter_button,
            add_pdf_report_diferencias_por_item_detalle_button,
        )
        btn_pdf_diff_item = add_pdf_report_diferencias_por_item_button(frm, db_path=DB_NAME, button_text="Diferencias por Item")
        try:
            btn_pdf_diff_item.grid(row=29, column=2, pady=8)
        except Exception:
            pass
        # Button to show only differences with absolute value greater than given threshold
        btn_pdf_diff_threshold = add_pdf_report_diferencias_threshold_button(frm, db_path=DB_NAME, button_text="Diferencias > X")
        try:
            btn_pdf_diff_threshold.grid(row=30, column=2, pady=8)
        except Exception:
            pass
        # Button for differences grouped by counter, location and item
        btn_pdf_diff_counter = add_pdf_report_diferencias_por_counter_button(frm, db_path=DB_NAME, button_text="Diferencias por Counter/Loc/Item")
        try:
            btn_pdf_diff_counter.grid(row=31, column=2, pady=8)
        except Exception:
            pass
        # Button for differences summary from inventory_count_res
        try:
            try:
                from ui_pdf_report_resumen import add_pdf_report_diferencias_resumen_button as add_pdf_report_diferencias_resumen_button
            except Exception:
                from ui_pdf_report import add_pdf_report_diferencias_resumen_button as add_pdf_report_diferencias_resumen_button
            btn_pdf_diff_resum = add_pdf_report_diferencias_resumen_button(frm, db_path=DB_NAME, button_text="Diferencias Resumen")
            try:
                btn_pdf_diff_resum.grid(row=33, column=2, pady=8)
            except Exception:
                pass
        except Exception:
            pass
        # Button for detailed differences per item (asks for item code)
        try:
            btn_pdf_diff_item_det = add_pdf_report_diferencias_por_item_detalle_button(frm, db_path=DB_NAME, button_text="Diferencias Item Detalle")
            try:
                btn_pdf_diff_item_det.grid(row=32, column=2, pady=8)
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        pass

    # --- Callbacks principales (adaptados) ---
    def import_catalog():
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        rename_map = {
            "number": "code_item", "code": "code_item", "codigo": "code_item",
            "description": "description_item", "desc": "description_item",
            "current": "current_inventory", "inventory": "current_inventory"
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if "code_item" not in df.columns:
            messagebox.showerror("Error", "El CSV debe contener la columna 'code_item' o 'number'/'code'")
            return
        df["code_item"] = df["code_item"].astype(str).str.strip()
        if "description_item" in df.columns:
            df["description_item"] = df["description_item"].astype(str).str.strip()
        else:
            df["description_item"] = ""
        if "current_inventory" in df.columns:
            df["current_inventory"] = pd.to_numeric(df["current_inventory"].replace("", "0"), errors="coerce").fillna(0).astype(int)
        else:
            df["current_inventory"] = 0
        conn = sqlite3.connect(DB_NAME)
        df[["code_item", "description_item", "current_inventory"]].to_sql("items", conn, if_exists="replace", index=False)
        conn.close()
        messagebox.showinfo("OK", "Catálogo importado correctamente")

    def buscar_item(event=None):
        code = entry_code.get().strip()
        if not code:
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT description_item, current_inventory FROM items WHERE code_item = ?", (code,))
        row = cur.fetchone()
        if not row:
            alt = code.lstrip("0")
            if alt:
                cur.execute("SELECT description_item, current_inventory FROM items WHERE code_item = ?", (alt,))
                row = cur.fetchone()
        # Si ya existen registros para este code_item, mostrar ventana de confirmación
        cur.execute("SELECT * FROM inventory_count WHERE code_item = ? ORDER BY count_date, counter_name, deposit_id, rack_id", (code,))
        existing = cur.fetchall()
        if existing:
            info = '\n'.join([
                f"FECHA: {r[8]}, CONTADOR: {r[1]}, DEPÓSITO: {r[10]}, RACK: {r[11]}, TOTAL: {r[5]}" for r in existing
            ])
            respuesta = messagebox.askyesno(
                "Registro existente",
                f"Ya existe(n) registro(s) con CODE_ITEM '{code}':\n\n{info}\n\n¿Deseas agregar el nuevo registro igualmente?"
            )
            if not respuesta:
                conn.close()
                entry_code.focus_set()
                entry_code.selection_range(0, tk.END)
                return
        conn.close()
        if row:
            entry_desc.config(state="normal")
            entry_desc.delete(0, tk.END)
            entry_desc.insert(0, row[0])
            entry_desc.config(state="readonly")
            lbl_current.config(text=f"Inventario actual: {row[1]}")
            entry_boxqty.focus_set()
            try:
                entry_boxqty.selection_range(0, tk.END)
            except Exception:
                pass
        else:
            messagebox.showerror("Error", "Código no encontrado")
            entry_code.focus_set()

    def guardar():
        try:
            name = combo_name.get()
            code = entry_code.get().strip()
            boxqty = int(entry_boxqty.get())
            boxunitqty = int(entry_boxunitqty.get())
            boxunittotal = boxqty * boxunitqty
            magazijn = int(entry_mag.get())
            winkel = int(entry_win.get())
            selected_date = date_entry.get_date() if DateEntry else datetime.now().date()
            deposit_idx = combo_deposit.current()
            rack_idx = combo_rack.current()
            if deposit_idx < 0 or rack_idx < 0:
                messagebox.showerror("Error", "Selecciona Deposit y Rack")
                return
            deposit_id = deposits_list[deposit_idx][0]
            rack_id = racks_list[rack_idx][0]
            deposit_name = deposits_list[deposit_idx][1]
            rack_name = racks_list[rack_idx][1]
            location = f"{deposit_name} - {rack_name}"
            lbl_location.config(text=location)
        except ValueError:
            messagebox.showerror("Error", "Cantidades inválidas")
            return
        if not name or not code:
            messagebox.showerror("Error", "Faltan datos")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        # Ya no se valida si el código existe en inventory_count; se permite múltiples registros para el mismo code_item
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        row = cur.fetchone()
        stored_code = code
        if not row:
            alt = code.lstrip("0")
            if alt:
                cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (alt,))
                row = cur.fetchone()
                if row:
                    stored_code = alt
        if not row:
            messagebox.showerror("Error", "Código inválido")
            conn.close()
            return
        actual = row[0]
        boxqty = int(entry_boxqty.get())
        boxunitqty = int(entry_boxunitqty.get())
        boxunittotal = boxqty * boxunitqty
        total = boxunittotal + magazijn + winkel
        diff = total - actual
        remark = entry_remark.get().strip()[:100]
        cur.execute("""
            INSERT INTO inventory_count
            (counter_name, code_item, magazijn, winkel, total, current_inventory, difference, count_date, location, deposit_id, rack_id, boxqty, boxunitqty, boxunittotal, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, stored_code, magazijn, winkel, total, actual, diff, selected_date.isoformat(), location, deposit_id, rack_id, boxqty, boxunitqty, boxunittotal, remark))
        conn.commit()
        conn.close()
        entry_code.delete(0, tk.END)
        entry_desc.config(state="normal"); entry_desc.delete(0, tk.END); entry_desc.config(state="readonly")
        entry_boxqty.delete(0, tk.END); entry_boxqty.insert(0, "0")
        entry_boxunitqty.delete(0, tk.END); entry_boxunitqty.insert(0, "0")
        entry_boxunittotal.config(state="normal"); entry_boxunittotal.delete(0, tk.END); entry_boxunittotal.insert(0, "0"); entry_boxunittotal.config(state="readonly")
        entry_mag.delete(0, tk.END); entry_mag.insert(0, "0")
        entry_win.delete(0, tk.END); entry_win.insert(0, "0")
        entry_remark.delete(0, tk.END)
        lbl_location.config(text="")
        entry_code.focus_set()
        msg_guardado.set("Registro guardado")
        root.after(2000, lambda: msg_guardado.set(""))

    def export_data():
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                 filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")])
        if not file_path:
            return
        conn = sqlite3.connect(DB_NAME)
        try:
            df = pd.read_sql_query("""
                SELECT c.id, c.counter_name, c.code_item,
                       COALESCE(i.description_item, '') AS description_item,
                       c.boxqty, c.boxunitqty, c.boxunittotal,
                       c.magazijn, c.winkel, c.total, c.current_inventory, c.difference,
                       d.deposit_description AS deposit_name, r.rack_description AS rack_name,
                       c.location, c.count_date
                FROM inventory_count c
                LEFT JOIN items i ON i.code_item = c.code_item
                LEFT JOIN deposits d ON d.deposit_id = c.deposit_id
                LEFT JOIN racks r ON r.rack_id = c.rack_id
                ORDER BY c.counter_name
            """, conn)
        except Exception as e:
            conn.close()
            messagebox.showerror("Error", f"Error al leer la base de datos: {e}")
            return
        conn.close()
        try:
            if file_path.lower().endswith(".csv"):
                df.to_csv(file_path, index=False)
            else:
                try:
                    df.to_excel(file_path, index=False, engine="openpyxl")
                except (ImportError, ModuleNotFoundError):
                    csv_path = file_path[:-5] + ".csv" if file_path.lower().endswith(".xlsx") else file_path + ".csv"
                    df.to_csv(csv_path, index=False)
                    opened = False
                    try:
                        if sys.platform.startswith("win"):
                            os.startfile(csv_path)
                            opened = True
                        else:
                            import subprocess
                            opener = "xdg-open" if sys.platform.startswith("linux") else "open"
                            subprocess.Popen([opener, csv_path])
                            opened = True
                    except Exception:
                        opened = False
                    if opened:
                        messagebox.showwarning("Aviso", f"No se encontró 'openpyxl'. Se guardó como CSV y se abrió: {csv_path}\nInstala openpyxl si quieres exportar directamente a .xlsx (ej: .venv\\Scripts\\activate && python -m pip install openpyxl)")
                    else:
                        messagebox.showwarning("Aviso", f"No se encontró 'openpyxl'. Se guardó como CSV: {csv_path}\nInstala openpyxl si quieres .xlsx (ej: .venv\\Scripts\\activate && python -m pip install openpyxl)\nPuedes abrir el CSV manualmente con Excel si está instalado.")
                    return
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar: {e}")
            return
        messagebox.showinfo("OK", f"Exportado correctamente: {file_path}")

    # Asociar eventos
    def on_code_enter(event=None):
        buscar_item()
        # Si el foco sigue en entry_code (por error), no mover
        if entry_code.focus_get() == entry_code:
            return
        entry_boxqty.focus_set()
    entry_code.bind("<Return>", on_code_enter)

    root.mainloop()

if __name__ == "__main__":
    main()
