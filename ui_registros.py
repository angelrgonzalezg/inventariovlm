import tkinter as tk
from tkinter import ttk, messagebox
from db_utils import get_deposits, get_racks
import sqlite3
from datetime import datetime

DB_NAME = 'inventariovlm.db'

def mostrar_registros(root):
    # --- Lógica migrada desde app.py ---
    def cargar_datos(order_by="code_item", filter_code=None):
        valid_fields = [
            "id", "counter_name", "count_date", "deposit_id", "rack_id", "location", "code_item",
            "boxqty", "boxunitqty", "boxunittotal", "magazijn", "winkel", "total", "current_inventory", "difference"
        ]
        col_sql = order_by if order_by in valid_fields else "counter_name"
        for r in tree.get_children():
            tree.delete(r)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            query = (
                "SELECT c.id, c.counter_name, c.count_date, c.deposit_id, c.rack_id, c.location, c.code_item, "
                "c.boxqty, c.boxunitqty, c.boxunittotal, c.magazijn, c.winkel, c.total, c.current_inventory, c.difference "
                "FROM inventory_count c"
            )
            params = ()
            if filter_code:
                query += " WHERE c.code_item = ?"
                params = (filter_code,)
            query += f" ORDER BY {col_sql}"
            cur.execute(query, params)
            rows = cur.fetchall()
            print(f"[ui_registros] cargar_datos: fetched {len(rows)} rows (filter={filter_code})")
            if rows:
                print("[ui_registros] first row sample:", rows[0])
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

    cols = ("id", "counter_name", "count_date", "deposit_id", "rack_id", "location", "code_item", "boxqty", "boxunitqty", "boxunittotal", "magazijn", "winkel", "total", "current_inventory", "difference")
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
    edit_boxqty = ttk.Entry(frm, width=8)
    edit_boxunitqty = ttk.Entry(frm, width=8)
    edit_boxunittotal = ttk.Entry(frm, width=10, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    status_total = ttk.Label(frm, text="", foreground="red")

    # Combobox de depósito y rack
    deposits_list = get_deposits()
    deposits_display = [d[1] for d in deposits_list]
    edit_deposit = ttk.Combobox(frm, values=deposits_display, state="readonly", width=18)
    edit_rack = ttk.Combobox(frm, values=[], state="readonly", width=18)

    # Entradas adicionales
    edit_location = ttk.Entry(frm, width=18, state="readonly")
    edit_date = ttk.Entry(frm, width=18)

    # Filtro por código
    lbl_filter = ttk.Label(frm, text="Filtrar código:")
    edit_filter = ttk.Entry(frm, width=12)
    btn_filter = ttk.Button(frm, text="Filtrar", command=lambda: cargar_datos(filter_code=edit_filter.get().strip() or None))
    btn_clear = ttk.Button(frm, text="Limpiar filtro", command=lambda: (edit_filter.delete(0, tk.END), cargar_datos()))

    # racks_list se actualizará dinámicamente
    racks_list = []

    edit_counter.grid(row=0, column=0, padx=2, pady=2)
    edit_code.grid(row=0, column=1, padx=2, pady=2)
    edit_boxqty.grid(row=0, column=2, padx=2, pady=2)
    edit_boxunitqty.grid(row=0, column=3, padx=2, pady=2)
    edit_boxunittotal.grid(row=0, column=4, padx=2, pady=2)
    edit_mag.grid(row=0, column=5, padx=2, pady=2)
    edit_win.grid(row=0, column=6, padx=2, pady=2)
    edit_total.grid(row=0, column=7, padx=2, pady=2)
    status_total.grid(row=0, column=8, padx=2, pady=2)
    edit_current.grid(row=0, column=9, padx=2, pady=2)
    edit_diff.grid(row=0, column=10, padx=2, pady=2)
    edit_deposit.grid(row=0, column=11, padx=2, pady=2)
    edit_rack.grid(row=0, column=12, padx=2, pady=2)
    edit_location.grid(row=0, column=13, padx=2, pady=2)
    edit_date.grid(row=0, column=14, padx=2, pady=2)
    lbl_filter.grid(row=1, column=0, padx=2, pady=2)
    edit_filter.grid(row=1, column=1, padx=2, pady=2)
    btn_filter.grid(row=1, column=2, padx=2, pady=2)
    btn_clear.grid(row=1, column=3, padx=2, pady=2)

    # (Botones de acción creados más abajo, después de definir las funciones)

    # (Eliminada la segunda definición de tree)
    def on_edit_deposit_change(event=None):
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
        nonlocal racks_list
        # get_racks returns a callable (inner); call it with deposit_id
        try:
            racks_list = get_racks()(deposit_id)
        except Exception:
            racks_list = []
        # racks_list may be list of tuples (id, description) or list of strings
        racks_display_local = [r[1] if isinstance(r, (list, tuple)) and len(r) > 1 else r for r in racks_list]
        edit_rack['values'] = racks_display_local
        if racks_display_local:
            edit_rack.current(0)
        else:
            edit_rack.set("")

    edit_deposit.bind("<<ComboboxSelected>>", on_edit_deposit_change)

    # Recalcular boxunittotal y total en tiempo real al editar cajas/unidades/sueltos/tienda
    def update_calculated_fields(event=None):
        try:
            boxqty_val = int(edit_boxqty.get() or 0)
        except Exception:
            boxqty_val = 0
        try:
            boxunit_val = int(edit_boxunitqty.get() or 0)
        except Exception:
            boxunit_val = 0
        try:
            magazijn_val = int(edit_mag.get() or 0)
        except Exception:
            magazijn_val = 0
        try:
            winkel_val = int(edit_win.get() or 0)
        except Exception:
            winkel_val = 0
        boxunittotal_val = boxqty_val * boxunit_val
        total_val = boxunittotal_val + magazijn_val + winkel_val
        # update fields (handle readonly toggling)
        try:
            edit_boxunittotal.config(state="normal")
            edit_boxunittotal.delete(0, tk.END)
            edit_boxunittotal.insert(0, str(boxunittotal_val))
            edit_boxunittotal.config(state="readonly")
        except Exception:
            pass
        try:
            edit_total.config(state="normal")
            edit_total.delete(0, tk.END)
            edit_total.insert(0, str(total_val))
            edit_total.config(state="readonly")
        except Exception:
            pass
        # show indicator if total differs from current inventory
        try:
            cur_inv = int(edit_current.get() or 0)
        except Exception:
            cur_inv = 0
        if total_val != cur_inv:
            status_total.config(text=f"Dif: {total_val - cur_inv}")
        else:
            status_total.config(text="OK", foreground="green")

    edit_boxqty.bind("<KeyRelease>", update_calculated_fields)
    edit_boxunitqty.bind("<KeyRelease>", update_calculated_fields)
    edit_mag.bind("<KeyRelease>", update_calculated_fields)
    edit_win.bind("<KeyRelease>", update_calculated_fields)
    # keyboard shortcuts
    win.bind('<Control-s>', lambda e: actualizar_registro())
    win.bind('<Delete>', lambda e: eliminar_registro())
    win.bind('<Escape>', lambda e: win.destroy())

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals order: id, counter_name, count_date, deposit_id, rack_id, location, code_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[2])
        code_val = vals[6]
        edit_code.delete(0, tk.END); edit_code.insert(0, code_val)
        # try to load description and current inventory from items
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT description_item, current_inventory FROM items WHERE code_item = ?", (code_val,))
            item = cur.fetchone()
            if item:
                edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, item[0]); edit_desc.config(state="readonly")
                edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, item[1]); edit_current.config(state="readonly")
        finally:
            try: conn.close()
            except Exception: pass

        edit_boxqty.delete(0, tk.END); edit_boxqty.insert(0, vals[7])
        edit_boxunitqty.delete(0, tk.END); edit_boxunitqty.insert(0, vals[8])
        edit_boxunittotal.config(state="normal"); edit_boxunittotal.delete(0, tk.END); edit_boxunittotal.insert(0, vals[9]); edit_boxunittotal.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[10])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[11])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[12]); edit_total.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[14]); edit_diff.config(state="readonly")
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, vals[5]); edit_location.config(state="readonly")

        # set deposit and rack by id (vals[3] and vals[4])
        try:
            deposit_id_val = vals[3]
            rack_id_val = vals[4]
        except Exception:
            deposit_id_val = None
            rack_id_val = None
        if deposit_id_val is not None:
            # find deposit name
            dep_name = ""
            for d in deposits_list:
                if d[0] == deposit_id_val:
                    dep_name = d[1]
                    break
            if dep_name:
                edit_deposit.set(dep_name)
                nonlocal racks_list
                try:
                    racks_list = get_racks()(deposit_id_val)
                except Exception:
                    racks_list = []
                racks_display_local = [r[1] if isinstance(r, (list, tuple)) and len(r) > 1 else r for r in racks_list]
                edit_rack['values'] = racks_display_local
                # find rack name from rack_id_val
                rack_name = ""
                for r in racks_list:
                    # r may be (id, description) or a single value
                    if isinstance(r, (list, tuple)) and len(r) > 1:
                        if r[0] == rack_id_val:
                            rack_name = r[1]
                            break
                    else:
                        # if racks are simple values, compare directly to rack_id_val
                        if r == rack_id_val or str(r) == str(rack_id_val):
                            rack_name = r
                            break
                
                if rack_name:
                    edit_rack.set(rack_name)
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
            boxqty = int(edit_boxqty.get() or 0)
            boxunitqty = int(edit_boxunitqty.get() or 0)
            magazijn = int(edit_mag.get() or 0)
            winkel = int(edit_win.get() or 0)
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
            if isinstance(r, (list, tuple)) and len(r) > 1:
                if r[1] == rack_name:
                    rack_id = r[0]
                    break
            else:
                if str(r) == str(rack_name):
                    # if rack list contains simple values, use that value as id
                    rack_id = r
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
        # derived quantities
        boxunittotal = boxqty * boxunitqty
        total = boxunittotal + magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")
        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, boxqty=?, boxunitqty=?, boxunittotal=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        # keep current filter if any
        cargar_datos(filter_code=edit_filter.get().strip() or None)
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

    # Botones de acción: Actualizar, Eliminar, Cerrar (creados aquí tras definir las funciones)
    btn_update = ttk.Button(frm, text="Actualizar", command=actualizar_registro)
    btn_delete = ttk.Button(frm, text="Eliminar", command=eliminar_registro)
    btn_close = ttk.Button(frm, text="Cerrar", command=win.destroy)
    btn_update.grid(row=1, column=4, padx=6, pady=2)
    btn_delete.grid(row=1, column=5, padx=6, pady=2)
    btn_close.grid(row=1, column=6, padx=6, pady=2)

    # Mostrar los datos al abrir la ventana
    cargar_datos()
