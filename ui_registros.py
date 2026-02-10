import tkinter as tk
from tkinter import ttk, messagebox
from db_utils import get_deposits, get_racks
import sqlite3
from datetime import datetime

DB_NAME = 'inventariovlm.db'

def mostrar_registros(root):
    # --- Lógica migrada desde app.py ---
    def cargar_datos(order_by="counter_name"):
        valid_fields = [
            "counter_name", "count_date", "deposit_id", "rack_id", "location", "code_item",
            "boxqty", "boxunitqty", "boxunittotal", "magazijn", "winkel", "total", "current_inventory", "difference"
        ]
        col_sql = order_by if order_by in valid_fields else "counter_name"
        for r in tree.get_children():
            tree.delete(r)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            cur.execute(f"""
                SELECT c.counter_name, c.count_date, c.deposit_id, c.rack_id, c.location, c.code_item, c.boxqty, c.boxunitqty, c.boxunittotal, c.magazijn, c.winkel, c.total, c.current_inventory, c.difference
                FROM inventory_count c
                ORDER BY {col_sql}
            """)
            rows = cur.fetchall()
            if not rows:
                messagebox.showinfo("Sin datos", "No hay registros para mostrar.")
            for row in rows:
                tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Error de consulta", f"No se pudo cargar registros: {e}")
        finally:
            conn.close()

    def on_ordenar(col):
        cargar_datos(col)

    win = tk.Toplevel(root)
    win.title("Registros de Inventario")
    win.geometry("1800x700")

    cols = ("counter_name", "count_date", "deposit_id", "rack_id", "location", "code_item", "boxqty", "boxunitqty", "boxunittotal", "magazijn", "winkel", "total", "current_inventory", "difference")
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

    # Entradas principales
    edit_counter = ttk.Entry(frm, width=14)
    edit_code = ttk.Entry(frm, width=12)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")

    # Combobox de depósito y rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=18)
    edit_rack = ttk.Combobox(frm, values=[], state="readonly", width=18)

    # Entradas adicionales
    edit_location = ttk.Entry(frm, width=18, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    # racks_list se actualizará dinámicamente
    racks_list = []

    edit_mag.grid(row=0, column=3, padx=2, pady=2)
    edit_win.grid(row=0, column=4, padx=2, pady=2)
    edit_total.grid(row=0, column=5, padx=2, pady=2)
    edit_current.grid(row=0, column=6, padx=2, pady=2)
    edit_diff.grid(row=0, column=7, padx=2, pady=2)
    edit_deposit.grid(row=0, column=8, padx=2, pady=2)
    edit_rack.grid(row=0, column=9, padx=2, pady=2)
    edit_location.grid(row=0, column=10, padx=2, pady=2)
    edit_date.grid(row=0, column=11, padx=2, pady=2)

    # (Eliminada la segunda definición de tree)
    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        nonlocal racks_list
        racks_list = get_racks(deposit_id)
        racks_display_local = [r[1] for r in racks_list]
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
            nonlocal racks_list
            racks_list = get_racks(deposit_id)
            racks_display_local = [r[1] for r in racks_list]
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

    tree.bind("<<TreeviewSelect>>", on_seleccionar)

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

    # Aquí puedes agregar los botones y layout para actualizar/eliminar, etc.
    # ...

    # Mostrar los datos al abrir la ventana
    cargar_datos()
