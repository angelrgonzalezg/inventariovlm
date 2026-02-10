# Helper para rutas de recursos (PyInstaller compatible)
def resource_path(relative_path):
    try:
        # PyInstaller crea una carpeta temporal y almacena el path en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# Inventario simple para laptop (Tkinter + SQLite)
# Autor: Angel

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
import sqlite3
import pandas as pd
from datetime import datetime
import sys
import os

DB_NAME = 'inventariovlm.db'

# Helper functions for deposits/racks
def obtener_deposits():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM deposits")
    deposits = [row[0] for row in cur.fetchall()]
    conn.close()
    return deposits

def obtener_racks(deposit_nombre):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id FROM deposits WHERE nombre = ?", (deposit_nombre,))
    deposit_id = cur.fetchone()
    racks = []
    if deposit_id:
        cur.execute("SELECT nombre FROM racks WHERE deposit_id = ?", (deposit_id[0],))
        racks = [row[0] for row in cur.fetchall()]
    conn.close()
    return racks




def get_deposits():
    """Obtener lista de depósitos desde la BD."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT deposit_id, deposit_description FROM deposits ORDER BY deposit_description")
        deposits = cur.fetchall()
        conn.close()
        return deposits
    except Exception:
        return []


def get_racks():
    """Obtener lista de racks desde la BD para un depósito específico (por id)."""
    def inner(deposit_id=None):
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            if deposit_id is not None:
                cur.execute("SELECT rack_id, rack_description FROM racks WHERE deposit_id = ? ORDER BY rack_description", (deposit_id,))
            else:
                cur.execute("SELECT rack_id, rack_description FROM racks ORDER BY rack_description")
            racks = cur.fetchall()
            conn.close()
            return racks
        except Exception:
            return []
    return inner

# --------------- CSV IMPORT ---------------
def import_catalog():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return

    # Leer todo como texto para preservar ceros a la izquierda y evitar problemas de tipado en el verificador
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)

    # Normalizar nombres comunes de columnas del CSV al esquema esperado
    rename_map = {
        "number": "code_item", "code": "code_item", "codigo": "code_item",
        "description": "description_item", "desc": "description_item",
        "current": "current_inventory", "inventory": "current_inventory"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Verificar que exista la columna de código
    if "code_item" not in df.columns:
        messagebox.showerror("Error", "El CSV debe contener la columna 'code_item' o 'number'/'code'")
        return

    # Normalizar valores: mantener ceros a la izquierda y limpiar espacios
    df["code_item"] = df["code_item"].astype(str).str.strip()
    if "description_item" in df.columns:
        df["description_item"] = df["description_item"].astype(str).str.strip()
    else:
        df["description_item"] = ""

    # Asegurar current_inventory como entero (si falta o está vacío, 0)
    if "current_inventory" in df.columns:
        df["current_inventory"] = pd.to_numeric(df["current_inventory"].replace("", "0"), errors="coerce").fillna(0).astype(int)
    else:
        df["current_inventory"] = 0

    # Guardar solo las columnas esperadas y reemplazar tabla
    conn = sqlite3.connect(DB_NAME)
    df[["code_item", "description_item", "current_inventory"]].to_sql("items", conn, if_exists="replace", index=False)
    conn.close()

    messagebox.showinfo("OK", "Catálogo importado correctamente")

# --------------- LOOKUP ITEM --------------
def buscar_item(event=None):
    global entry_code
    code = entry_code.get().strip()
    if not code:
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Búsqueda exacta primero
    cur.execute("SELECT description_item, current_inventory FROM items WHERE code_item = ?", (code,))
    row = cur.fetchone()

    # Si no hay resultado, intentar buscar versión sin ceros iniciales
    if not row:
        alt = code.lstrip("0")
        if alt:
            cur.execute("SELECT description_item, current_inventory FROM items WHERE code_item = ?", (alt,))
            row = cur.fetchone()

    # Antes de continuar, comprobar si ya existe un recuento para este código
    # (se compara tanto la forma tal cual como la versión sin ceros iniciales)
    cur.execute("SELECT COUNT(1) FROM inventory_count WHERE code_item = ?", (code,))
    if cur.fetchone()[0] > 0:
        conn.close()
        messagebox.showwarning("Aviso", "Ya existe un registro para este código en inventory_count. Por favor revise la data introducida.")
        entry_code.focus_set()
        return
    alt_check = code.lstrip("0")
    if alt_check:
        cur.execute("SELECT COUNT(1) FROM inventory_count WHERE code_item = ?", (alt_check,))
        if cur.fetchone()[0] > 0:
            conn.close()
            messagebox.showwarning("Aviso", "Ya existe un registro para este código (sin ceros iniciales) en inventory_count. Por favor revise la data introducida.")
            entry_code.focus_set()
            return

    conn.close()

    if row:
        entry_desc.config(state="normal")
        entry_desc.delete(0, tk.END)
        entry_desc.insert(0, row[0])
        entry_desc.config(state="readonly")
        lbl_current.config(text=f"Inventario actual: {row[1]}")

        # Colocar el foco en Magazijn y seleccionar su contenido para facilitar la entrada
        entry_mag.focus_set()
        try:
            entry_mag.selection_range(0, tk.END)
        except Exception:
            pass
    else:
        messagebox.showerror("Error", "Código no encontrado")
        entry_code.focus_set()

# --------------- SAVE COUNT ---------------
def guardar():
    try:
        name = combo_name.get()
        code = entry_code.get().strip()
        magazijn = int(entry_mag.get())
        winkel = int(entry_win.get())
        # Fecha seleccionada
        if DateEntry:
            selected_date = date_entry.get_date()
        else:
            try:
                selected_date = datetime.fromisoformat(date_txt := (date_entry.get() if 'date_entry' in globals() else ''))
                selected_date = selected_date.date()
            except Exception:
                selected_date = datetime.now().date()
        # Deposit y Rack seleccionados
        deposit_idx = combo_deposit.current()
        rack_idx = combo_rack.current()
        if deposit_idx < 0 or rack_idx < 0:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = deposits_list[deposit_idx][0]
        rack_id = racks_list[rack_idx][0]
        deposit_name = deposits_list[deposit_idx][1]
        rack_name = racks_list[rack_idx][1]
        # Generar location automáticamente
        location = f"{deposit_name} - {rack_name}"
        # Mostrar location en el label display-only
        lbl_location.config(text=location)
    except ValueError:
        messagebox.showerror("Error", "Cantidades inválidas")
        return

    if not name or not code:
        messagebox.showerror("Error", "Faltan datos")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Validación: si ya existe un registro para este código (o versión sin ceros) evitar duplicado
    cur.execute("SELECT COUNT(1) FROM inventory_count WHERE code_item = ?", (code,))
    if cur.fetchone()[0] > 0:
        conn.close()
        messagebox.showwarning("Aviso", "Ya existe un registro para este código en inventory_count. Por favor revise la data introducida.")
        entry_code.focus_set()
        return
    alt_check = code.lstrip("0")
    if alt_check:
        cur.execute("SELECT COUNT(1) FROM inventory_count WHERE code_item = ?", (alt_check,))
        if cur.fetchone()[0] > 0:
            conn.close()
            messagebox.showwarning("Aviso", "Ya existe un registro para este código (sin ceros iniciales) en inventory_count. Por favor revise la data introducida.")
            entry_code.focus_set()
            return

    # Obtener current_inventory desde items (con fallback sin ceros)
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
    total = magazijn + winkel
    diff = total - actual

    cur.execute("""
        INSERT INTO inventory_count
        (counter_name, code_item, magazijn, winkel, total, current_inventory, difference, deposit_id, rack_id, location, count_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, stored_code, magazijn, winkel, total, actual, diff, deposit_id, rack_id, location, selected_date.isoformat()))

    conn.commit()
    conn.close()
    # Limpiar campos después de guardar
    entry_code.delete(0, tk.END)
    entry_desc.config(state="normal"); entry_desc.delete(0, tk.END); entry_desc.config(state="readonly")
    entry_mag.delete(0, tk.END); entry_mag.insert(0, "0")
    entry_win.delete(0, tk.END); entry_win.insert(0, "0")
    # Reset location label
    lbl_location.config(text="")
    # Mantener Deposit y Rack seleccionados, pero podrías resetear si lo prefieres
    entry_code.focus_set()

    messagebox.showinfo("OK", "Registro guardado")

    # Restablecer campos: código vacío, cantidades a 0, descripción limpia
    entry_code.delete(0, tk.END)
    entry_mag.delete(0, tk.END)
    entry_mag.insert(0, "0")
    entry_win.delete(0, tk.END)
    entry_win.insert(0, "0")
    entry_desc.config(state="normal")
    entry_desc.delete(0, tk.END)
    entry_desc.config(state="readonly")
    try:
        lbl_location.config(text="")
    except Exception:
        pass
    # reset date to today
    try:
        if DateEntry:
            date_entry.set_date(datetime.now().date())
        else:
            date_entry.delete(0, tk.END); date_entry.insert(0, datetime.now().date().isoformat())
    except Exception:
        pass

    # Poner foco en el campo Código para la siguiente entrada
    entry_code.focus_set()

# --------------- EXPORT DATA --------------
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
                   c.magazijn, c.winkel, c.total, c.current_inventory, c.difference, c.location, c.count_date
            FROM inventory_count c
            LEFT JOIN items i ON i.code_item = c.code_item
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
                # fallback a CSV si falta openpyxl
                csv_path = file_path[:-5] + ".csv" if file_path.lower().endswith(".xlsx") else file_path + ".csv"
                df.to_csv(csv_path, index=False)
                # Intentar abrir el CSV con la aplicación por defecto (Excel si está instalado)
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

# ----------------- UI ---------------------
def mostrar_registros():
    # Ventana para ver, ordenar, editar y eliminar registros (incluye description via JOIN)
    def cargar_datos(order_by="counter_name"):
        mapping = {
            "id": "c.id",
            "counter_name": "c.counter_name",
            "code_item": "c.code_item",
            "description_item": "i.description_item",
            "magazijn": "c.magazijn",
            "winkel": "c.winkel",
            "total": "c.total",
            "current_inventory": "c.current_inventory",
            "difference": "c.difference",
            "location": "c.location",
            "count_date": "c.count_date"
        }
        col_sql = mapping.get(order_by, "c.counter_name")

        for r in tree.get_children():
            tree.delete(r)

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT c.id, c.counter_name, c.code_item, COALESCE(i.description_item, ''), c.magazijn, c.winkel,
                   c.total, c.current_inventory, c.difference, c.location, c.count_date
            FROM inventory_count c
            LEFT JOIN items i ON i.code_item = c.code_item
            ORDER BY {col_sql}
        """)
        for row in cur.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    def on_ordenar(col):
        cargar_datos(col)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1000x420")

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "location", "count_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        width = 120
        if col == "description_item":
            width = 260
        elif col == "id":
            width = 60
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    # Nuevos dropdowns para Deposit y Rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    get_racks_func = get_racks()
    if deposits_list:
        racks_list = get_racks_func(deposits_list[0][0])
    else:
        racks_list = []
    racks_display = [r[1] for r in racks_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=14)
    edit_rack = ttk.Combobox(frm, values=racks_display, state="readonly", width=14)
    edit_location = ttk.Entry(frm, width=25, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        racks_list_local = get_racks_func(deposit_id)
        racks_display_local = [r[1] for r in racks_list_local]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, deposit, rack, location, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[11]); edit_location.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[12])

        if vals[9] in deposits_display:
            edit_deposit.set(vals[9])
            idx = deposits_display.index(vals[9])
            deposit_id = deposits_list[idx][0]
            racks_list_local = get_racks_func(deposit_id)
            racks_display_local = [r[1] for r in racks_list_local]
            edit_rack['values'] = racks_display_local
            if vals[10] in racks_display_local:
                edit_rack.set(vals[10])
            elif racks_display_local:
                edit_rack.current(0)
            else:
                edit_rack.set("")
        else:
            edit_deposit.set("")
            edit_rack['values'] = []
            edit_rack.set("")

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        counter = edit_counter.get().strip()
        code = edit_code.get().strip()
        date_txt = edit_date.get().strip()

        try:
            magazijn = int(edit_mag.get())
            winkel = int(edit_win.get())
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros")
            return

        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name or not rack_name:
            messagebox.showerror("Error", "Selecciona Deposit y Rack")
            return
        deposit_id = None
        rack_id = None
        for d in deposits_list:
            if d[1] == deposit_name:
                deposit_id = d[0]
                break
        for r in racks_list:
            if r[1] == rack_name:
                rack_id = r[0]
                break
        if deposit_id is None or rack_id is None:
            messagebox.showerror("Error", "Depósito o Rack inválido")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items")
            return
        current_inv = item_row[0]
        total = magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        cargar_datos()
        messagebox.showinfo("OK", "Registro actualizado")

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro")
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory_count WHERE id = ?", (id_reg,))
        conn.commit()
        conn.close()
        cargar_datos()
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_location, edit_date):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado")