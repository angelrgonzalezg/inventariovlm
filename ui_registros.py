import tkinter as tk
from tkinter import ttk, messagebox
from db_utils import get_deposits, get_racks
import sqlite3
from datetime import datetime

DB_NAME = 'inventariovlm.db'


class _Tooltip:
    """Simple tooltip for tkinter widgets.

    Usage: _Tooltip(widget, "text to show")
    """
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        widget.bind("<Enter>", self.enter, add=True)
        widget.bind("<Leave>", self.leave, add=True)
        widget.bind("<Motion>", self.motion, add=True)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def motion(self, event=None):
        # update position for the tooltip
        self.x = event.x_root + 10
        self.y = event.y_root + 10

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            try:
                self.widget.after_cancel(id_)
            except Exception:
                pass

    def showtip(self):
        if self.tipwindow or not self.text:
            return
        try:
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{self.x}+{self.y}")
            label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                             background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                             font=("tahoma", "8", "normal"))
            label.pack(ipadx=4, ipady=2)
        except Exception:
            self.tipwindow = None

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        try:
            if tw:
                tw.destroy()
        except Exception:
            pass

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
            messagebox.showerror("Error de consulta", f"No se pudo cargar registros: {e}", parent=win)
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
    # code_item should be visible but not editable: keep normal state but block keys
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

    # Tooltips: brief labels shown on hover for the edit fields
    try:
        _Tooltip(edit_counter, "Contador: nombre de la persona que contó")
        _Tooltip(edit_code, "Código del ítem (use el formato del inventario)")
        _Tooltip(edit_desc, "Descripción del producto (solo lectura)")
        _Tooltip(edit_boxqty, "Cajas: cantidad de cajas contadas")
        _Tooltip(edit_boxunitqty, "U/caja: unidades por caja")
        _Tooltip(edit_boxunittotal, "Tot. U/cajas: cajas * U/caja (solo lectura)")
        _Tooltip(edit_mag, "Magazijn: unidades sueltas en almacén")
        _Tooltip(edit_win, "Winkel: unidades sueltas en tienda")
        _Tooltip(edit_total, "Total: totales calculados (solo lectura)")
        _Tooltip(edit_current, "Actual: inventario actual en la tabla items (solo lectura)")
        _Tooltip(edit_diff, "Diferencia: total - actual (solo lectura)")
        _Tooltip(edit_deposit, "Depósito: seleccionar depósito")
        _Tooltip(edit_rack, "Rack: seleccionar rack dentro del depósito")
        _Tooltip(edit_location, "Ubicación: depósito - rack (solo lectura)")
        _Tooltip(edit_date, "Fecha del conteo (ISO o deje vacío para fecha actual)")
        _Tooltip(edit_filter, "Escriba un código y presione Filtrar")
    except Exception:
        # Tooltips are best-effort; if anything goes wrong keep UI functional
        pass

    # block typing into the code field (user should not edit it here)
    def _block_edit_keys(event=None):
        return "break"
    edit_code.bind("<Key>", _block_edit_keys)

    # (Botones de acción creados más abajo, después de definir las funciones)

    # (Eliminada la segunda definición de tree)
    def on_edit_deposit_change(event=None):
        nonlocal racks_list
        idx = edit_deposit.current()
        if idx < 0:
            edit_rack['values'] = []
            return
        deposit_id = deposits_list[idx][0]
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
        try:
            print(f"[ui_registros] on_seleccionar values={vals}")
            print(f"[ui_registros] code_val repr: {repr(vals[6])}")
        except Exception:
            pass
        # vals order: id, counter_name, count_date, deposit_id, rack_id, location, code_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference
        edit_counter.delete(0, tk.END); edit_counter.insert(0, vals[1])
        edit_date.delete(0, tk.END); edit_date.insert(0, vals[2])
        code_val = vals[6]
        # set code field (blocked for typing)
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
        # normalize types: try to convert ids to int for comparisons/calls
        try:
            deposit_id_val = int(deposit_id_val)
        except Exception:
            pass
        try:
            rack_id_val = int(rack_id_val)
        except Exception:
            pass

        nonlocal racks_list
        if deposit_id_val is not None:
            # find deposit name
            dep_name = ""
            for d in deposits_list:
                # compare as ints or strings to be robust
                if (isinstance(d[0], int) and d[0] == deposit_id_val) or (str(d[0]) == str(deposit_id_val)):
                    dep_name = d[1]
                    break
            if dep_name:
                edit_deposit.set(dep_name)
                # Prefer to lookup rack description directly by rack_id in the racks table
                try:
                    conn2 = sqlite3.connect(DB_NAME)
                    cur2 = conn2.cursor()
                    cur2.execute("SELECT rack_description FROM racks WHERE rack_id = ?", (rack_id_val,))
                    rr = cur2.fetchone()
                    conn2.close()
                except Exception:
                    rr = None

                try:
                    racks_list = get_racks()(deposit_id_val)
                except Exception:
                    racks_list = []
                racks_display_local = [r[1] if isinstance(r, (list, tuple)) and len(r) > 1 else r for r in racks_list]
                # if we found a rack description by id, prefer that and ensure it's in the combobox values
                if rr and rr[0]:
                    rack_name = rr[0]
                    # ensure the combobox values include this rack description
                    if rack_name not in racks_display_local:
                        edit_rack['values'] = [rack_name] + racks_display_local
                    else:
                        edit_rack['values'] = racks_display_local
                    edit_rack.set(rack_name)
                else:
                    # fallback: try to match by id inside the fetched racks_list
                    rack_name = ""
                    for r in racks_list:
                        if isinstance(r, (list, tuple)) and len(r) > 1:
                            if (isinstance(r[0], int) and r[0] == rack_id_val) or (str(r[0]) == str(rack_id_val)):
                                rack_name = r[1]
                                break
                        else:
                            if (isinstance(r, int) and r == rack_id_val) or str(r) == str(rack_id_val):
                                rack_name = r
                                break

                    if rack_name:
                        edit_rack['values'] = racks_display_local
                        edit_rack.set(rack_name)
                    else:
                        # final fallback: if there are any racks for this deposit, select first; else clear
                        edit_rack['values'] = racks_display_local
                        if racks_display_local:
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
            messagebox.showerror("Error", "Selecciona un registro", parent=win)
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
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros", parent=win)
            return
        deposit_name = edit_deposit.get()
        rack_name = edit_rack.get()
        if not deposit_name:
            messagebox.showerror("Error", "Selecciona Deposit", parent=win)
            return
        deposit_id = None
        rack_id = None
        dep_name_norm = deposit_name.strip() if isinstance(deposit_name, str) else deposit_name
        rack_name_norm = rack_name.strip() if isinstance(rack_name, str) else rack_name

        # Try to resolve deposit_id from the in-memory list (case-insensitive)
        for d in deposits_list:
            try:
                if isinstance(d, (list, tuple)):
                    # d[1] is usually the description
                    if len(d) >= 2 and str(d[1]).strip().lower() == str(dep_name_norm).lower():
                        deposit_id = d[0]
                        break
                    # support other tuple shapes where description may be at index 2
                    if len(d) >= 3 and str(d[2]).strip().lower() == str(dep_name_norm).lower():
                        deposit_id = d[0]
                        break
                    # allow matching if user pasted an id into the combobox
                    if str(d[0]).strip() == str(dep_name_norm):
                        deposit_id = d[0]
                        break
                else:
                    if str(d).strip().lower() == str(dep_name_norm).lower():
                        # single-value list case: we need to lookup id from DB
                        deposit_id = None
                        break
            except Exception:
                continue

        # Resolve rack_id primarily by querying the `racks` table (preferred over in-memory lists).
        # Strategies tried: numeric id, exact with deposit, exact without deposit, startswith with deposit, LIKE without deposit.
        try:
            conn_r = sqlite3.connect(DB_NAME)
            cur_r = conn_r.cursor()
            # 1) numeric id
            try:
                cand = int(rack_name_norm)
                cur_r.execute("SELECT rack_id FROM racks WHERE rack_id = ? LIMIT 1", (cand,))
                rr = cur_r.fetchone()
                if rr:
                    rack_id = rr[0]
            except Exception:
                pass

            # 2) exact match with deposit
            if rack_id is None and rack_name_norm and deposit_id is not None:
                try:
                    cur_r.execute("SELECT rack_id FROM racks WHERE rack_description = ? AND deposit_id = ? COLLATE NOCASE LIMIT 1", (rack_name_norm, deposit_id))
                    rr = cur_r.fetchone()
                    if rr:
                        rack_id = rr[0]
                except Exception:
                    pass

            # 3) exact match without deposit
            if rack_id is None and rack_name_norm:
                try:
                    cur_r.execute("SELECT rack_id FROM racks WHERE rack_description = ? COLLATE NOCASE LIMIT 1", (rack_name_norm,))
                    rr = cur_r.fetchone()
                    if rr:
                        rack_id = rr[0]
                except Exception:
                    pass

            # 4) startswith within deposit
            if rack_id is None and rack_name_norm and deposit_id is not None:
                try:
                    cur_r.execute("SELECT rack_id FROM racks WHERE rack_description LIKE ? AND deposit_id = ? LIMIT 1", (f"{rack_name_norm}%", deposit_id))
                    rr = cur_r.fetchone()
                    if rr:
                        rack_id = rr[0]
                except Exception:
                    pass

            # 5) LIKE fallback without deposit
            if rack_id is None and rack_name_norm:
                try:
                    cur_r.execute("SELECT rack_id FROM racks WHERE rack_description LIKE ? LIMIT 1", (f"%{rack_name_norm}%",))
                    rr = cur_r.fetchone()
                    if rr:
                        rack_id = rr[0]
                except Exception:
                    pass

            try:
                conn_r.close()
            except Exception:
                pass
        except Exception:
            rack_id = None

        # Fallback: if deposit_id couldn't be determined earlier, resolve it from DB now
        if deposit_id is None:
            try:
                cur2 = sqlite3.connect(DB_NAME).cursor()
                cur2.execute("SELECT deposit_id FROM deposits WHERE deposit_description = ? COLLATE NOCASE LIMIT 1", (dep_name_norm,))
                rr = cur2.fetchone()
                if rr:
                    deposit_id = rr[0]
                else:
                    # try matching by number or trimmed description
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

        # Fallback: DB lookup for rack by description (case-insensitive), prefer same-deposit match
        if rack_id is None:
            try:
                conn3 = sqlite3.connect(DB_NAME)
                cur3 = conn3.cursor()
                if deposit_id is not None:
                    cur3.execute("SELECT rack_id FROM racks WHERE rack_description = ? AND deposit_id = ? COLLATE NOCASE LIMIT 1", (rack_name_norm, deposit_id))
                    rr = cur3.fetchone()
                    if rr:
                        rack_id = rr[0]
                if rack_id is None:
                    # try exact match without deposit
                    cur3.execute("SELECT rack_id FROM racks WHERE rack_description = ? COLLATE NOCASE LIMIT 1", (rack_name_norm,))
                    rr = cur3.fetchone()
                    if rr:
                        rack_id = rr[0]
                if rack_id is None:
                    # try partial match
                    if deposit_id is not None:
                        cur3.execute("SELECT rack_id FROM racks WHERE rack_description LIKE ? AND deposit_id = ? LIMIT 1", (f"%{rack_name_norm}%", deposit_id))
                        rr = cur3.fetchone()
                        if rr:
                            rack_id = rr[0]
                    if rack_id is None:
                        cur3.execute("SELECT rack_id FROM racks WHERE rack_description LIKE ? LIMIT 1", (f"%{rack_name_norm}%",))
                        rr = cur3.fetchone()
                        if rr:
                            rack_id = rr[0]
                try:
                    conn3.close()
                except Exception:
                    pass
            except Exception:
                rack_id = None

        if deposit_id is None:
            messagebox.showerror("Error", f"Depósito inválido (deposit: {deposit_name} -> {deposit_id})", parent=win)
            return
        # If rack_id couldn't be resolved, allow storing NULL or numeric string
        if rack_id is None:
            # try interpreting the rack_name as an id (user may have pasted numeric id)
            try:
                rack_id = int(rack_name_norm)
            except Exception:
                rack_id = None

        # If still None, try to extract rack from location (format: 'Deposit - Rack') and retry DB lookup
        if rack_id is None:
            loc_val = ''
            try:
                loc_val = edit_location.get().strip()
            except Exception:
                loc_val = ''
            if not rack_name_norm and loc_val and ' - ' in loc_val:
                candidate = loc_val.split(' - ', 1)[1].strip()
                if candidate:
                    rack_name_norm = candidate

        # As a last-resort DB fuzzy search for rack_name
        if rack_id is None and rack_name_norm:
            try:
                conn_f = sqlite3.connect(DB_NAME)
                cur_f = conn_f.cursor()
                # prefer same-deposit exact match (case-insensitive)
                if deposit_id is not None:
                    cur_f.execute("SELECT rack_id FROM racks WHERE rack_description = ? AND deposit_id = ? COLLATE NOCASE LIMIT 1", (rack_name_norm, deposit_id))
                    rr = cur_f.fetchone()
                    if rr:
                        rack_id = rr[0]
                if rack_id is None:
                    # try startswith
                    if deposit_id is not None:
                        cur_f.execute("SELECT rack_id FROM racks WHERE rack_description LIKE ? AND deposit_id = ? LIMIT 1", (f"{rack_name_norm}%", deposit_id))
                        rr = cur_f.fetchone()
                        if rr:
                            rack_id = rr[0]
                    if rack_id is None:
                        cur_f.execute("SELECT rack_id FROM racks WHERE rack_description LIKE ? LIMIT 1", (f"%{rack_name_norm}%",))
                        rr = cur_f.fetchone()
                        if rr:
                            rack_id = rr[0]
                try:
                    conn_f.close()
                except Exception:
                    pass
            except Exception:
                pass
        # DEBUG: print resolution results to help diagnose missing rack_id
        try:
            print(f"[ui_registros] actualizar_registro: id={id_reg} deposit_name={deposit_name!r} dep_id_resolved={deposit_id!r} rack_name={rack_name!r} rack_id_resolved={rack_id!r}")
            print(f"[ui_registros] racks_list sample (first 6): {racks_list[:6]}")
        except Exception:
            pass
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT current_inventory FROM items WHERE code_item = ?", (code,))
        item_row = cur.fetchone()
        if not item_row:
            conn.close()
            messagebox.showerror("Error", "Código no válido en items", parent=win)
            return
        current_inv = item_row[0]
        # derived quantities
        boxunittotal = boxqty * boxunitqty
        total = boxunittotal + magazijn + winkel
        diff = total - current_inv
        location = f"{deposit_name} - {rack_name}"
        edit_location.config(state="normal"); edit_location.delete(0, tk.END); edit_location.insert(0, location); edit_location.config(state="readonly")
        print(f"[ui_registros] executing UPDATE for id={id_reg} with rack_id={rack_id}")
        cur.execute("""
            UPDATE inventory_count
            SET counter_name=?, code_item=?, boxqty=?, boxunitqty=?, boxunittotal=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, deposit_id=?, rack_id=?, location=?, count_date=?
            WHERE id=?
        """, (counter, code, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inv, diff, deposit_id, rack_id, location, date_txt or datetime.now().isoformat(), id_reg))
        conn.commit()
        conn.close()
        # keep current filter if any
        cargar_datos(filter_code=edit_filter.get().strip() or None)
        messagebox.showinfo("OK", "Registro actualizado", parent=win)

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro", parent=win)
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro?", parent=win):
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
        messagebox.showinfo("OK", "Registro eliminado", parent=win)

    # Botones de acción: Actualizar, Eliminar, Cerrar (creados aquí tras definir las funciones)
    btn_update = ttk.Button(frm, text="Actualizar", command=actualizar_registro)
    btn_delete = ttk.Button(frm, text="Eliminar", command=eliminar_registro)
    btn_close = ttk.Button(frm, text="Cerrar", command=win.destroy)
    btn_update.grid(row=1, column=4, padx=6, pady=2)
    btn_delete.grid(row=1, column=5, padx=6, pady=2)
    btn_close.grid(row=1, column=6, padx=6, pady=2)

    # --- Nueva UI: selector rápido de reportes + botón ejecutar ---
    rpt_options = [
        "Reporte por Deposito",
        "Reporte por contador",
        "Reporte Verificaion",
        "Reporte Diferencias",
        "Diferencias por Items",
        "Diferencias Resumen (inventory_count_res)",
        "Diferencias > X",
        "Diferencias por Couneter/Loc/Item",
        "Diferencia Item Detalle",
    ]
    lbl_rpt = ttk.Label(frm, text="Seleccionar reporte:")
    cmb_rpt = ttk.Combobox(frm, values=rpt_options, state="readonly", width=36)
    cmb_rpt.set(rpt_options[0])
    def ejecutar_reporte():
        sel = cmb_rpt.get().strip()
        if not sel:
            return
        # normalize key
        key = sel.lower().replace(" ", "").replace("/", "").replace("\u00a0", "")
        try:
            import ui_pdf_report as rpt
        except Exception as e:
            try:
                import ui_pdf_report_resumen as rpt
            except Exception:
                messagebox.showerror("Error", f"No se pudo cargar los reportes: {e}", parent=win)
                return

        try:
            if "deposito" in key and "por" in key:
                rpt.generate_pdf_report_por_deposito(win, db_path=DB_NAME)
            elif "contador" in key and "por" in key:
                rpt.generate_pdf_report_por_contador(win, db_path=DB_NAME)
            elif "verific" in key:
                rpt.generate_pdf_report_verificacion(win, db_path=DB_NAME)
            elif "diferencias>" in key or "diferencias>x" in key or ">x" in key:
                rpt.generate_pdf_report_diferencias_threshold(win, db_path=DB_NAME)
            elif "diferenciaporcounterlocitem" in key or "counterlocitem" in key or "counterlocitem" in key:
                rpt.generate_pdf_report_diferencias_por_counter(win, db_path=DB_NAME)
            elif "diferenciasporitems" in key or "poritem" in key:
                rpt.generate_pdf_report_diferencias_por_item(win, db_path=DB_NAME)
            elif "resumen" in key or "inventory_count_res" in key:
                fn = getattr(rpt, "generate_pdf_report_diferencias_resumen", None)
                if fn is not None:
                    fn(win, db_path=DB_NAME)
                else:
                    try:
                        import ui_pdf_report_resumen as rpt_res
                        rpt_res.generate_pdf_report_diferencias_resumen(win, db_path=DB_NAME)
                    except Exception:
                        raise
            elif "diferenciaitemdetalle" in key or "itemdetalle" in key:
                rpt.generate_pdf_report_diferencias_item_detalle(win, db_path=DB_NAME)
            elif "diferencias" in key:
                rpt.generate_pdf_report_diferencias(win, db_path=DB_NAME)
            else:
                # default fallback: try open main differences report
                rpt.generate_pdf_report_diferencias(win, db_path=DB_NAME)
        except Exception as e:
            messagebox.showerror("Error", f"Error al ejecutar el reporte: {e}", parent=win)

    btn_rpt_exec = ttk.Button(frm, text="Ejecutar reporte", command=ejecutar_reporte)
    def _run_resumen():
        try:
            try:
                mod = __import__('ui_pdf_report')
                fn = getattr(mod, 'generate_pdf_report_diferencias_resumen', None)
            except Exception:
                try:
                    mod = __import__('ui_pdf_report_resumen')
                    fn = getattr(mod, 'generate_pdf_report_diferencias_resumen', None)
                except Exception:
                    fn = None
            if fn is None:
                messagebox.showerror("Error", "Función de reporte 'generate_pdf_report_diferencias_resumen' no encontrada", parent=win)
                return
            fn(win, db_path=DB_NAME)
        except Exception as e:
            messagebox.showerror("Error", f"Error al ejecutar reporte resumen: {e}", parent=win)

    btn_rpt_resum = ttk.Button(frm, text="Diferencias Resumen", command=_run_resumen)
    lbl_rpt.grid(row=1, column=7, padx=6, pady=2)
    cmb_rpt.grid(row=1, column=8, padx=6, pady=2)
    btn_rpt_exec.grid(row=1, column=9, padx=6, pady=2)
    # place the resumen button to the right of Ejecutar
    try:
        btn_rpt_resum.grid(row=1, column=10, padx=6, pady=2)
    except Exception:
        btn_rpt_resum.pack(padx=6, pady=2)

    # Mostrar los datos al abrir la ventana
    cargar_datos()


def mostrar_registros_resumen(root):
    """Similar window to `mostrar_registros` but operating on `inventory_count_res` summary table."""
    def cargar_datos(order_by="code_item", order_dir="ASC", filter_code=None):
        valid_fields = [
            "id", "code_item", "description_item", "boxqty", "boxunitqty", "boxunittotal",
            "magazijn", "winkel", "total", "current_inventory", "difference", "updated_date"
        ]
        col_sql = order_by if order_by in valid_fields else "code_item"
        order_dir_sql = "ASC" if str(order_dir).upper() != "DESC" else "DESC"
        for r in tree.get_children():
            tree.delete(r)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            query = (
                "SELECT id, code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, updated_date "
                "FROM inventory_count_res"
            )
            params = ()
            if filter_code:
                query += " WHERE code_item = ?"
                params = (filter_code,)
            query += f" ORDER BY {col_sql} {order_dir_sql}"
            cur.execute(query, params)
            rows = cur.fetchall()
            print(f"[ui_registros_resumen] cargar_datos: fetched {len(rows)} rows (filter={filter_code})")
            for row in rows:
                tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Error de consulta", f"No se pudo cargar registros resumen: {e}", parent=win)
        finally:
            conn.close()

    # track current sort settings
    sort_field = "code_item"
    sort_dir = "ASC"

    def on_ordenar(col):
        nonlocal sort_field, sort_dir
        # if clicking same column, toggle direction
        if col == sort_field:
            sort_dir = "DESC" if sort_dir == "ASC" else "ASC"
        else:
            sort_field = col
            sort_dir = "ASC"
        # update UI control if present
        try:
            cmb_sort.set(sort_field)
            btn_dir.config(text=sort_dir)
        except Exception:
            pass
        cargar_datos(order_by=sort_field, order_dir=sort_dir)

    win = tk.Toplevel(root)
    win.title("Registros Resumen")
    # Make the window larger so more columns are visible
    win.geometry("2000x800")

    cols = ("id", "code_item", "description_item", "boxqty", "boxunitqty", "boxunittotal", "magazijn", "winkel", "total", "current_inventory", "difference", "updated_date")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
    for col in cols:
        heading = col.replace("_", " ").title()
        tree.heading(col, text=heading, command=lambda c=col: on_ordenar(c))
        # wider defaults per column to fit more data on large window
        if col == "id":
            width = 60
        elif col == "code_item":
            width = 140
        elif col == "description_item":
            width = 320
        elif col in ("boxqty", "boxunitqty", "boxunittotal"):
            width = 100
        elif col in ("magazijn", "winkel"):
            width = 90
        elif col in ("total", "current_inventory", "difference"):
            width = 110
        elif col == "updated_date":
            width = 160
        else:
            width = 120
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=6, pady=6)

    frm = ttk.Frame(win, padding=6)
    frm.pack(fill="x", padx=6, pady=(0,6))

    # Entradas principales (summary fields)
    edit_code = ttk.Entry(frm, width=14)
    edit_desc = ttk.Entry(frm, width=36, state="readonly")
    edit_boxqty = ttk.Entry(frm, width=8)
    edit_boxunitqty = ttk.Entry(frm, width=8)
    edit_boxunittotal = ttk.Entry(frm, width=10, state="readonly")
    edit_mag = ttk.Entry(frm, width=8)
    edit_win = ttk.Entry(frm, width=8)
    edit_total = ttk.Entry(frm, width=10, state="readonly")
    edit_current = ttk.Entry(frm, width=10, state="readonly")
    edit_diff = ttk.Entry(frm, width=10, state="readonly")
    edit_updated = ttk.Entry(frm, width=18)

    lbl_filter = ttk.Label(frm, text="Filtrar código:")
    edit_filter = ttk.Entry(frm, width=12)
    btn_filter = ttk.Button(frm, text="Filtrar", command=lambda: cargar_datos(filter_code=edit_filter.get().strip() or None))
    btn_clear = ttk.Button(frm, text="Limpiar filtro", command=lambda: (edit_filter.delete(0, tk.END), cargar_datos()))

    edit_code.grid(row=0, column=0, padx=2, pady=2)
    edit_desc.grid(row=0, column=1, padx=2, pady=2)
    edit_boxqty.grid(row=0, column=2, padx=2, pady=2)
    edit_boxunitqty.grid(row=0, column=3, padx=2, pady=2)
    edit_boxunittotal.grid(row=0, column=4, padx=2, pady=2)
    edit_mag.grid(row=0, column=5, padx=2, pady=2)
    edit_win.grid(row=0, column=6, padx=2, pady=2)
    edit_total.grid(row=0, column=7, padx=2, pady=2)
    edit_current.grid(row=0, column=8, padx=2, pady=2)
    edit_diff.grid(row=0, column=9, padx=2, pady=2)
    edit_updated.grid(row=0, column=10, padx=2, pady=2)
    lbl_filter.grid(row=1, column=0, padx=2, pady=2)
    edit_filter.grid(row=1, column=1, padx=2, pady=2)
    btn_filter.grid(row=1, column=2, padx=2, pady=2)
    btn_clear.grid(row=1, column=3, padx=2, pady=2)

    # Sorting controls: field selector and direction toggle (user-friendly labels)
    lbl_sort = ttk.Label(frm, text="Ordenar por:")
    # Map display labels -> SQL columns
    sort_display_map = {"Código": "code_item", "Diferencia": "difference"}
    sort_display_values = list(sort_display_map.keys())
    reverse_sort_map = {v: k for k, v in sort_display_map.items()}
    cmb_sort = ttk.Combobox(frm, values=sort_display_values, state="readonly", width=18)
    cmb_sort.set(sort_display_values[0])
    def on_sort_field_change(event=None):
        nonlocal sort_field, sort_dir
        sel = cmb_sort.get()
        sort_field = sort_display_map.get(sel, "code_item")
        sort_dir = "ASC"
        btn_dir.config(text=sort_dir)
        cargar_datos(order_by=sort_field, order_dir=sort_dir, filter_code=edit_filter.get().strip() or None)
    cmb_sort.bind("<<ComboboxSelected>>", on_sort_field_change)

    btn_dir = ttk.Button(frm, text="ASC", width=6)
    # toggle direction
    def toggle_dir():
        nonlocal sort_dir
        sort_dir = "DESC" if sort_dir == "ASC" else "ASC"
        btn_dir.config(text=sort_dir)
        cargar_datos(order_by=sort_field, order_dir=sort_dir, filter_code=edit_filter.get().strip() or None)
    btn_dir.config(command=toggle_dir)

    # Place sorting controls on their own row to separate them from the filter line
    lbl_sort.grid(row=2, column=0, padx=6, pady=2, sticky="w")
    cmb_sort.grid(row=2, column=1, padx=2, pady=2, sticky="w")
    btn_dir.grid(row=2, column=2, padx=2, pady=2, sticky="w")
    # Checkbox to show/hide the updated_date column to gain horizontal space
    show_date_var = tk.BooleanVar(value=True)
    def toggle_date_column():
        if show_date_var.get():
            tree.column('updated_date', width=160, minwidth=50)
            tree.heading('updated_date', text='Updated Date')
        else:
            # hide by shrinking width to zero
            tree.column('updated_date', width=0, minwidth=0)
            tree.heading('updated_date', text='')
    chk_date = ttk.Checkbutton(frm, text="Mostrar fecha", variable=show_date_var, command=toggle_date_column)
    chk_date.grid(row=2, column=3, padx=6, pady=2, sticky="w")

    # block typing into the code field if desired
    def _block_edit_keys(event=None):
        return "break"
    edit_code.bind("<Key>", _block_edit_keys)

    def on_seleccionar(event=None):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        # vals order: id, code_item, description_item, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, current_inventory, difference, updated_date
        edit_code.delete(0, tk.END); edit_code.insert(0, vals[1])
        edit_desc.config(state="normal"); edit_desc.delete(0, tk.END); edit_desc.insert(0, vals[2]); edit_desc.config(state="readonly")
        edit_boxqty.delete(0, tk.END); edit_boxqty.insert(0, vals[3])
        edit_boxunitqty.delete(0, tk.END); edit_boxunitqty.insert(0, vals[4])
        edit_boxunittotal.config(state="normal"); edit_boxunittotal.delete(0, tk.END); edit_boxunittotal.insert(0, vals[5]); edit_boxunittotal.config(state="readonly")
        edit_mag.delete(0, tk.END); edit_mag.insert(0, vals[6])
        edit_win.delete(0, tk.END); edit_win.insert(0, vals[7])
        edit_total.config(state="normal"); edit_total.delete(0, tk.END); edit_total.insert(0, vals[8]); edit_total.config(state="readonly")
        edit_current.config(state="normal"); edit_current.delete(0, tk.END); edit_current.insert(0, vals[9]); edit_current.config(state="readonly")
        edit_diff.config(state="normal"); edit_diff.delete(0, tk.END); edit_diff.insert(0, vals[10]); edit_diff.config(state="readonly")
        edit_updated.delete(0, tk.END); edit_updated.insert(0, vals[11])

    tree.bind("<<TreeviewSelect>>", on_seleccionar)

    def actualizar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro", parent=win)
            return
        id_reg = tree.item(sel, "values")[0]
        code = edit_code.get().strip()
        desc = edit_desc.get().strip()
        try:
            boxqty = int(edit_boxqty.get() or 0)
            boxunitqty = int(edit_boxunitqty.get() or 0)
            magazijn = int(edit_mag.get() or 0)
            winkel = int(edit_win.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Magazijn y Winkel deben ser números enteros", parent=win)
            return
        boxunittotal = boxqty * boxunitqty
        total = boxunittotal + magazijn + winkel
        try:
            cur = sqlite3.connect(DB_NAME).cursor()
            cur.execute("""
                UPDATE inventory_count_res
                SET code_item=?, description_item=?, boxqty=?, boxunitqty=?, boxunittotal=?, magazijn=?, winkel=?, total=?, current_inventory=?, difference=?, updated_date=?
                WHERE id=?
            """, (code, desc, boxqty, boxunitqty, boxunittotal, magazijn, winkel, total, int(edit_current.get() or 0), total - int(edit_current.get() or 0), edit_updated.get() or datetime.now().isoformat(), id_reg))
            conn = cur.connection
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar registro resumen: {e}", parent=win)
            return
        cargar_datos(filter_code=edit_filter.get().strip() or None)
        messagebox.showinfo("OK", "Registro actualizado", parent=win)

    def eliminar_registro():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Error", "Selecciona un registro", parent=win)
            return
        id_reg = tree.item(sel, "values")[0]
        if not messagebox.askyesno("Confirmar", "¿Eliminar este registro resumen?", parent=win):
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("DELETE FROM inventory_count_res WHERE id = ?", (id_reg,))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar registro resumen: {e}", parent=win)
            return
        cargar_datos()
        for w in (edit_code, edit_desc, edit_boxqty, edit_boxunitqty, edit_boxunittotal, edit_mag, edit_win, edit_total, edit_current, edit_diff, edit_updated):
            try:
                w.config(state="normal"); w.delete(0, tk.END)
                if w in (edit_desc, edit_boxunittotal, edit_total, edit_current, edit_diff):
                    w.config(state="readonly")
            except Exception:
                pass
        messagebox.showinfo("OK", "Registro eliminado", parent=win)

    # Botones de acción
    btn_update = ttk.Button(frm, text="Actualizar", command=actualizar_registro)
    btn_delete = ttk.Button(frm, text="Eliminar", command=eliminar_registro)
    btn_close = ttk.Button(frm, text="Cerrar", command=win.destroy)
    btn_update.grid(row=1, column=4, padx=6, pady=2)
    btn_delete.grid(row=1, column=5, padx=6, pady=2)
    btn_close.grid(row=1, column=6, padx=6, pady=2)

    cargar_datos()
