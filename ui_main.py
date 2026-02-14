import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from db_utils import get_deposits, get_racks
from ui_registros import mostrar_registros
import pandas as pd
from datetime import datetime
import sys
import os
import sqlite3
DB_NAME = 'inventariovlm.db'
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
        # Formatear fecha a ISO
        if 'count_date' in df.columns:
            df['count_date'] = df['count_date'].apply(lambda d: datetime.strptime(d, '%d-%m-%Y').date().isoformat() if d else datetime.now().date().isoformat())
            # Insertar en la base de datos
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            insertados = 0
            for _, row in df.iterrows():
                cur.execute("SELECT * FROM inventory_count WHERE code_item = ? ORDER BY count_date, counter_name, deposit_id, rack_id", (row['code_item'],))
                existing = cur.fetchall()
                if existing:
                    # Mostrar los registros existentes en un diálogo, ordenados
                    info = '\n'.join([
                        f"FECHA: {r[8]}, CONTADOR: {r[1]}, DEPÓSITO: {r[10]}, RACK: {r[11]}, TOTAL: {r[5]}" for r in existing
                    ])
                    respuesta = messagebox.askyesno(
                        "Registro existente",
                        f"Ya existe(n) registro(s) con CODE_ITEM '{row['code_item']}':\n\n{info}\n\n¿Deseas agregar el nuevo registro igualmente?"
                    )
                    if not respuesta:
                        # Si responde NO, saltar este registro
                        continue
                cur.execute("""
                    INSERT INTO inventory_count
                    (counter_name, code_item, magazijn, winkel, total, current_inventory, difference, count_date, location, deposit_id, rack_id, boxqty, boxunitqty, boxunittotal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get('counter_name', ''),
                    row.get('code_item', ''),
                    row.get('magazijn', 0),
                    row.get('winkel', 0),
                    row.get('total', 0),
                    0, # current_inventory (no viene en CSV)
                    row.get('total', 0), # difference (igual a total si no hay current_inventory)
                    row.get('count_date', datetime.now().date().isoformat()),
                    '', # location (puedes mejorar si quieres)
                    row.get('deposit_id', 0),
                    row.get('rack_id', 0),
                    row.get('boxqty', 0),
                    row.get('boxunitqty', 0),
                    row.get('boxunittotal', 0)
                ))
                insertados += 1
            conn.commit()
            conn.close()
            messagebox.showinfo("Importación completada", f"Se importaron {insertados} registros desde Deposit_1_Victoria.csv")

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
    msg_guardado = tk.StringVar()
    lbl_guardado = ttk.Label(frm, textvariable=msg_guardado, foreground="green")
    lbl_guardado.grid(row=20, column=2, padx=8, sticky="w")
    btn_registros = ttk.Button(frm, text="Ver Registros", command=lambda: mostrar_registros(root))
    btn_registros.grid(row=22, column=1, pady=8)

    # Botón para generar reporte PDF (usa ui_pdf_report.add_pdf_report_button)
    from ui_pdf_report import add_pdf_report_button, add_pdf_report_por_deposito_button, add_pdf_report_por_contador_button
    btn_pdf = add_pdf_report_button(frm, db_path=DB_NAME, button_text="Generar PDF")
    try:
        btn_pdf.grid(row=22, column=2, pady=8)
    except Exception:
        pass

    # Botón para reporte por depósito
    btn_pdf_deposito = add_pdf_report_por_deposito_button(frm, db_path=DB_NAME, button_text="Reporte por Depósito")
    try:
        btn_pdf_deposito.grid(row=23, column=2, pady=8)
    except Exception:
        pass

    # Botón para reporte por contador
    btn_pdf_contador = add_pdf_report_por_contador_button(frm, db_path=DB_NAME, button_text="Reporte por Contador")
    try:
        btn_pdf_contador.grid(row=24, column=2, pady=8)
    except Exception:
        pass

    # Botón reporte de verificación (orden por id)
    try:
        from ui_pdf_report import add_pdf_report_verificacion_button
        btn_pdf_verif = add_pdf_report_verificacion_button(frm, db_path=DB_NAME, button_text="Reporte Verificación")
        try:
            btn_pdf_verif.grid(row=25, column=2, pady=8)
        except Exception:
            pass
    except Exception:
        # if import fails, ignore
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
