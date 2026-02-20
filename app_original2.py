# Inventario simple para laptop (Tkinter + SQLite)
# Autor: Angel

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "inventariovlm.db"

# ---------------- DB INIT -----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            code_item TEXT(10) PRIMARY KEY,
            description_item TEXT,
            current_inventory INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory_count (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            counter_name TEXT,
            code_item TEXT(10),
            magazijn INTEGER,
            winkel INTEGER,
            total INTEGER,
            current_inventory INTEGER,
            difference INTEGER,
            count_date TEXT,
            FOREIGN KEY (code_item) REFERENCES items(code_item)
        )
    """)

    conn.commit()
    conn.close()

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
    if not row:
        alt = code.lstrip("0")
        if alt:
            cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (alt,))
            row = cur.fetchone()

    if not row:
        messagebox.showerror("Error", "Código inválido")
        conn.close()
        return

    actual = row[0]
    total = magazijn + winkel
    diff = total - actual

    cur.execute("""
        INSERT INTO inventory_count
        (counter_name, code_item, magazijn, winkel, total, current_inventory, difference, count_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, code, magazijn, winkel, total, actual, diff, datetime.now().isoformat()))

    conn.commit()
    conn.close()

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
                   c.magazijn, c.winkel, c.total, c.current_inventory, c.difference, c.count_date
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
                messagebox.showwarning("Aviso", f"No se encontró 'openpyxl'. Se guardó como CSV: {csv_path}\nInstala openpyxl si quieres .xlsx (ej: .venv\\Scripts\\activate && python -m pip install openpyxl)")
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
            "count_date": "c.count_date"
        }
        col_sql = mapping.get(order_by, "c.counter_name")

        for r in tree.get_children():
            tree.delete(r)

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT c.id, c.counter_name, c.code_item, COALESCE(i.description_item, ''), c.magazijn, c.winkel,
                   c.total, c.current_inventory, c.difference, c.count_date
            FROM inventory_count c
            LEFT JOIN items i ON i.code_item = c.code_item
            ORDER BY {col_sql}
        """)
        for row in cur.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    def on_ordenar(col):
        cargar_datos(col)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals: id, counter_name, code_item, description, magazijn, winkel, total, current_inventory, difference, count_date
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[2])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[3]); edit_desc.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[4])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[5])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[6]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[7]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[8]); edit_diff.config(state="readonly")
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[9])

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

        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, count_date=?
            WHERE id=?
        """, (counter, code, magazijn, winkel, total, current_inv, diff, date_txt or datetime.now().isoformat(), id_reg))
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
        for w in (edit_counter, edit_code, edit_desc, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_date):
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

    cols = ("id", "counter_name", "code_item", "description_item", "magazijn", "winkel", "total", "current_inventory", "difference", "count_date")
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
    edit_date = ttk.Entry(frm, width=18)

    ttk.Label(frm, text="Counter").grid(row=0, column=0, padx=3)
    edit_counter.grid(row=1, column=0, padx=3)
    ttk.Label(frm, text="Code").grid(row=0, column=1, padx=3)
    edit_code.grid(row=1, column=1, padx=3)
    ttk.Label(frm, text="Description").grid(row=0, column=2, padx=3)
    edit_desc.grid(row=1, column=2, padx=3)
    ttk.Label(frm, text="Magazijn").grid(row=0, column=3, padx=3)
    edit_mag.grid(row=1, column=3, padx=3)
    ttk.Label(frm, text="Winkel").grid(row=0, column=4, padx=3)
    edit_win.grid(row=1, column=4, padx=3)
    ttk.Label(frm, text="Total").grid(row=0, column=5, padx=3)
    edit_total.grid(row=1, column=5, padx=3)
    ttk.Label(frm, text="Current").grid(row=0, column=6, padx=3)
    edit_current.grid(row=1, column=6, padx=3)
    ttk.Label(frm, text="Diff").grid(row=0, column=7, padx=3)
    edit_diff.grid(row=1, column=7, padx=3)
    ttk.Label(frm, text="Date").grid(row=0, column=8, padx=3)
    edit_date.grid(row=1, column=8, padx=3)

    btn_frame = ttk.Frame(win)
    btn_frame.pack(fill="x", padx=6, pady=6)
    ttk.Button(btn_frame, text="Actualizar", command=actualizar_registro).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Eliminar", command=eliminar_registro).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Cerrar", command=win.destroy).pack(side="right", padx=6)

    tree.bind("<<TreeviewSelect>>", on_seleccionar)

    cargar_datos()

init_db()

root = tk.Tk()
root.title("Inventario VLM — CJ Electrical Supply (Draft Version)")
# Ventana más compacta
root.geometry("480x330")

# Forzar que el tamaño pedido se aplique y deshabilitar redimensionado
root.update_idletasks()
#root.resizable(False, False)
root.minsize(480, 330)
root.maxsize(480, 330)

# Frame con menos padding y anclado arriba (no expand)
frame = ttk.Frame(root, padding=6)
frame.pack(fill="x", anchor="n")

# Nombre
label_name = ttk.Label(frame, text="Processed by:")
label_name.grid(row=0, column=0, sticky="w", padx=(0,6), pady=2)
combo_name = ttk.Combobox(frame, values=["Luzmery", "Malina", "Victoria"], state="readonly")
combo_name.grid(row=0, column=1, sticky="ew", pady=2)
try:
    combo_name.current(0)
except Exception:
    pass

# Código
label_code = ttk.Label(frame, text="Code:")
label_code.grid(row=1, column=0, sticky="w", padx=(0,6), pady=2)
entry_code = ttk.Entry(frame)
entry_code.grid(row=1, column=1, sticky="ew", pady=2)
entry_code.bind("<Return>", buscar_item)

# Description
label_desc = ttk.Label(frame, text="Description:")
label_desc.grid(row=2, column=0, sticky="w", padx=(0,6), pady=2)
entry_desc = ttk.Entry(frame, state="readonly")
entry_desc.grid(row=2, column=1, sticky="ew", pady=2)

# Current inventory
lbl_current = ttk.Label(frame, text="Current inventory: ")
lbl_current.grid(row=3, column=1, sticky="w", pady=2)

# Magazijn
label_mag = ttk.Label(frame, text="Magazijn:")
label_mag.grid(row=4, column=0, sticky="w", padx=(0,6), pady=2)
entry_mag = ttk.Entry(frame)
entry_mag.grid(row=4, column=1, sticky="ew", pady=2)
entry_mag.insert(0, "0")

# Winkel
label_win = ttk.Label(frame, text="Winkel:")
label_win.grid(row=5, column=0, sticky="w", padx=(0,6), pady=2)
entry_win = ttk.Entry(frame)
entry_win.grid(row=5, column=1, sticky="ew", pady=2)
entry_win.insert(0, "0")

# Funciones de navegación entre campos
def focus_to_winkel(event=None):
    entry_win.focus_set()
    try:
        entry_win.selection_range(0, tk.END)
    except Exception:
        pass
    return "break"

def focus_to_save(event=None):
    btn_save.focus_set()
    return "break"

entry_mag.bind("<Return>", focus_to_winkel)
entry_win.bind("<Return>", focus_to_save)

# Buttons row: Import | Ver Registros | Save (misma línea, Import primero)
btn_row = ttk.Frame(frame)
##btn_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8,6))
btn_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 4))
# permitir distribución de espacio entre las 3 columnas del contenedor
##btn_row.columnconfigure(0, weight=1)
##btn_row.columnconfigure(1, weight=1)
##btn_row.columnconfigure(2, weight=1)
# Configurar columnas para buena distribución
for i in range(4):
    btn_row.columnconfigure(i, weight=1)

##btn_import = ttk.Button(btn_row, text="Import Catalog CSV", command=import_catalog, state="disabled")
##btn_import.grid(row=0, column=0, padx=6, sticky="w")
btn_import = ttk.Button(
    btn_row,
    text="Import Catalog CSV",
    command=import_catalog,
    state="disabled"
)
btn_import.grid(row=0, column=0, padx=4, sticky="w")

btn_export = ttk.Button(
    btn_row,
    text="Export Excel / CSV",
    command=export_data
)
btn_export.grid(row=0, column=1, padx=4)

##btn_registros = ttk.Button(btn_row, text="Ver Registros", command=mostrar_registros)
##btn_registros.grid(row=0, column=1, padx=6)
btn_registros = ttk.Button(
    btn_row,
    text="Ver Registros",
    command=mostrar_registros
)
btn_registros.grid(row=0, column=2, padx=4)

##btn_save = ttk.Button(btn_row, text="Save", command=guardar)
##btn_save.grid(row=0, column=2, padx=6, sticky="e")
btn_save = ttk.Button(
    btn_row,
    text="Save",
    command=guardar
)
btn_save.grid(row=0, column=3, padx=4, sticky="e")

# Export se mantiene en la fila siguiente (puedes moverlo si prefieres)
##btn_export = ttk.Button(frame, text="Export Excel / CSV", command=export_data)
##btn_export.grid(row=7, column=1, pady=(6,8))

frame.columnconfigure(1, weight=1)

root.mainloop()

