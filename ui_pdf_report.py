"""
ui_pdf_report.py

Utilities to add PDF report buttons and generate PDF reports from the
`inventory_count` table joined with items, deposits and racks.

Provides:
- add_pdf_report_button(parent_frame, db_path)
- add_pdf_report_por_contador_button(...)
- add_pdf_report_por_deposito_button(...)
- add_pdf_report_verificacion_button(...)

Each generator tries to open the generated PDF automatically (Windows/macOS/Linux).
"""

from __future__ import annotations

import os
import sys
import sqlite3
import subprocess
from typing import Optional
from tkinter import filedialog, messagebox

DEFAULT_DB = "inventariovlm.db"


def _fmt_int(x):
    """Format a value as integer with thousands separator (dot).

    Accepts numbers or strings; returns a string.
    """
    try:
        n = int(round(float(x)))
    except Exception:
        try:
            n = int(x)
        except Exception:
            n = 0
    return f"{n:,}".replace(',', '.')


def _open_pdf_file(file_path: str, parent: Optional[object] = None) -> bool:
    """Open a PDF file using a platform-appropriate command.

    Returns True if the open command was invoked successfully, False otherwise.
    If a `parent` tkinter widget is provided and opening fails, shows a warning
    dialog informing the user where the file was saved.
    """
    try:
        if os.name == "nt":
            os.startfile(file_path)
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
            return True
        # Linux / other
        subprocess.Popen(["xdg-open", file_path])
        return True
    except Exception as e:
        try:
            if parent is not None:
                messagebox.showwarning("Aviso",
                                       f"No se pudo abrir el PDF automáticamente: {e}\nArchivo generado: {file_path}",
                                       parent=parent)
        except Exception:
            pass
        return False


def _ensure_reportlab(parent: Optional[object] = None) -> bool:
    try:
        # imported lazily by callers
        import reportlab  # noqa: F401
        return True
    except Exception:
        messagebox.showerror("Error", "No se encontró 'reportlab'. Instala reportlab (ej: pip install reportlab)", parent=parent)
        return False


def _asksave(parent: object) -> Optional[str]:
    # backward-compatible: try to get a suggested name from parent._selected_report_name
    suggested = None
    try:
        if hasattr(parent, '_selected_report_name'):
            suggested = getattr(parent, '_selected_report_name')
    except Exception:
        suggested = None
    initial = None
    if suggested:
        try:
            initial = str(suggested).strip().replace(' ', '_')
        except Exception:
            initial = None
    return filedialog.asksaveasfilename(parent=parent, defaultextension=".pdf", initialfile=initial,
                                        filetypes=[("PDF files", "*.pdf")])


# ----------------- Button registration helpers -----------------


def _make_button(parent_frame, row: int, text: str, command):
    try:
        from tkinter import ttk
        btn = ttk.Button(parent_frame, text=text, command=command)
        try:
            btn.grid(row=row, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=text, command=command)
        try:
            btn.grid(row=row, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn


def add_pdf_report_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Generar PDF"):
    return _make_button(parent_frame, row=23, text=button_text, command=lambda: generate_pdf_report(parent_frame, db_path))


def add_pdf_report_por_contador_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Reporte por Contador"):
    return _make_button(parent_frame, row=25, text=button_text, command=lambda: generate_pdf_report_por_contador(parent_frame, db_path))


def add_pdf_report_por_deposito_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Reporte por Depósito"):
    return _make_button(parent_frame, row=24, text=button_text, command=lambda: generate_pdf_report_por_deposito(parent_frame, db_path))


def add_pdf_report_verificacion_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Reporte Verificación"):
    return _make_button(parent_frame, row=26, text=button_text, command=lambda: generate_pdf_report_verificacion(parent_frame, db_path))


def add_pdf_report_diferencias_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Reporte Diferencias"):
    return _make_button(parent_frame, row=27, text=button_text, command=lambda: generate_pdf_report_diferencias(parent_frame, db_path))


def add_pdf_report_diferencias_por_item_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Diferencias por Item"):
    return _make_button(parent_frame, row=28, text=button_text, command=lambda: generate_pdf_report_diferencias_por_item(parent_frame, db_path))


def add_pdf_report_diferencias_threshold_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Diferencias > X"):
    return _make_button(parent_frame, row=29, text=button_text, command=lambda: generate_pdf_report_diferencias_threshold(parent_frame, db_path))


def add_pdf_report_diferencias_por_counter_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Diferencias por Counter/Loc/Item"):
    return _make_button(parent_frame, row=30, text=button_text, command=lambda: generate_pdf_report_diferencias_por_counter(parent_frame, db_path))


def add_pdf_report_diferencias_resumen_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Diferencias Resumen"):
    try:
        # Prefer the small resumen module if available
        import ui_pdf_report_resumen as rpt_res
        return _make_button(parent_frame, row=33, text=button_text, command=lambda: rpt_res.generate_pdf_report_diferencias_resumen(parent_frame, db_path))
    except Exception:
        # fallback to invoking the local implementation
        return _make_button(parent_frame, row=33, text=button_text, command=lambda: _invoke_report_by_name('generate_pdf_report_diferencias_resumen', parent_frame, db_path))


# ----------------- Report generators -----------------


def generate_pdf_report(parent, db_path: str = DEFAULT_DB):
    """Generic report grouped by deposit -> rack with page break per deposit."""
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    sql = """
        SELECT c.id, c.counter_name, c.code_item,
               COALESCE(i.description_item, '') AS description_item,
               c.boxqty, c.boxunitqty, c.boxunittotal,
               c.magazijn, c.winkel, c.total, c.current_inventory, c.difference,
               COALESCE(d.deposit_description, '') AS deposit_name,
               COALESCE(r.rack_description, '') AS rack_name,
               c.location, c.count_date
        FROM inventory_count c
        LEFT JOIN items i ON i.code_item = c.code_item
        LEFT JOIN deposits d ON d.deposit_id = c.deposit_id
        LEFT JOIN racks r ON r.rack_id = c.rack_id
        ORDER BY deposit_name, rack_name, c.count_date, c.counter_name, c.code_item
    """

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    # group deposit -> rack -> rows
    grouped = []
    current_deposit = None
    current_rack = None
    deposit_block = None
    for row in rows:
        deposit_name = row[12] or "Sin depósito"
        rack_name = row[13] or "Sin rack"
        if deposit_name != current_deposit:
            deposit_block = {"deposit": deposit_name, "racks": {}}
            grouped.append(deposit_block)
            current_deposit = deposit_name
            current_rack = None
        if rack_name != current_rack:
            deposit_block["racks"][rack_name] = []
            current_rack = rack_name
        deposit_block["racks"][rack_name].append(row)

    # lazy imports for reportlab flowables
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    deposit_style = styles["Heading2"]
    rack_style = styles["Heading3"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte de Inventario", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["ID", "Contador", "Código", "Descripción", "Cajas", "U/caja", "Total cajas", "Magazijn", "Winkel", "Total", "Actual", "Difer.", "Ubicación", "Fecha"]

    for di, deposit_block in enumerate(grouped):
        story.append(Paragraph(f"Depósito: {deposit_block['deposit']}", deposit_style))
        story.append(Spacer(1, 6))
        for rack_name, items in deposit_block["racks"].items():
            story.append(Paragraph(f"Rack: {rack_name} — {len(items)} registros", rack_style))
            story.append(Spacer(1, 4))
            data = [col_headers]
            for r in items:
                data.append([
                    r[0] or "",
                    r[1] or "",
                    r[2] or "",
                    (r[3] or "")[:60],
                    _fmt_int(r[4] or 0),
                    _fmt_int(r[5] or 0),
                    _fmt_int(r[6] or 0),
                    _fmt_int(r[7] or 0),
                    _fmt_int(r[8] or 0),
                    _fmt_int(r[9] or 0),
                    _fmt_int(r[10] or 0),
                    _fmt_int(r[11] or 0),
                    r[14] or "",
                    r[15] or ""
                ])
            table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[30, 70, 60, 140, 35, 40, 45, 45, 40, 45, 40, 40, 90, 60])
            tbl_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
            # detect numeric headers and right-align those columns
            try:
                hdrs = data[0] if data else []
                numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
                ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                for i in ncols:
                    try:
                        tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                    except Exception:
                        pass
            except Exception:
                pass
            table.setStyle(tbl_style)
            story.append(table)
            story.append(Spacer(1, 8))
        if di < len(grouped) - 1:
            story.append(PageBreak())

    if not grouped:
        story.append(Paragraph("No hay registros para reportar.", normal))

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_por_contador(parent, db_path: str = DEFAULT_DB):
    # Ask which counters to include (multi-select). Reuse pattern from deposit selection.
    def _ask_select_counters(parent, db_path: str):
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception:
            return None

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT COALESCE(counter_name, '') FROM inventory_count ORDER BY 1")
            counters = [c[0] for c in cur.fetchall() if c is not None]
            conn.close()
        except Exception:
            return None

        if not counters:
            return None

        win = tk.Toplevel(parent)
        win.title('Seleccionar Contadores')
        win.transient(parent)
        win.grab_set()

        lbl = ttk.Label(win, text='Seleccione contadores (marca "Todos" o elija individualmente):')
        lbl.pack(padx=8, pady=(8, 4))

        canvas = tk.Canvas(win, borderwidth=0, height=200)
        frame_inner = ttk.Frame(canvas)
        vsb = ttk.Scrollbar(win, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True, padx=8, pady=4)
        canvas.create_window((0, 0), window=frame_inner, anchor='nw')

        def _on_frame_configure(event=None):
            try:
                canvas.configure(scrollregion=canvas.bbox('all'))
            except Exception:
                pass

        frame_inner.bind('<Configure>', _on_frame_configure)

        vars_list = []
        id_map = []
        todos_var = tk.IntVar(value=1)

        def _set_all(v=None):
            val = todos_var.get()
            for vv in vars_list:
                vv.set(bool(val))

        chk_all = ttk.Checkbutton(frame_inner, text='Todos', variable=todos_var, command=_set_all)
        chk_all.pack(anchor='w', pady=2)

        for c in counters:
            cname = c or ''
            var = tk.IntVar(value=1)
            cb = ttk.Checkbutton(frame_inner, text=cname if cname != '' else '(Sin nombre)', variable=var, onvalue=1, offvalue=0)
            cb.pack(anchor='w', padx=6)
            vars_list.append(var)
            id_map.append(cname)

        def _update_todos():
            try:
                all_on = all(v.get() for v in vars_list)
                todos_var.set(1 if all_on else 0)
            except Exception:
                pass

        for var in vars_list:
            try:
                var.trace_add('write', lambda *a: _update_todos())
            except Exception:
                try:
                    var.trace('w', lambda *a: _update_todos())
                except Exception:
                    pass

        sel_vals = None
        frm = ttk.Frame(win)
        frm.pack(padx=8, pady=8)

        def _on_ok():
            selected = [id_map[i] for i, v in enumerate(vars_list) if v.get()]
            nonlocal sel_vals
            sel_vals = selected if selected else None
            win.destroy()

        def _on_cancel():
            nonlocal sel_vals
            sel_vals = None
            win.destroy()

        btn_ok = ttk.Button(frm, text='OK', command=_on_ok)
        btn_ok.pack(side='left', padx=6)
        btn_cancel = ttk.Button(frm, text='Cancelar', command=_on_cancel)
        btn_cancel.pack(side='left', padx=6)

        parent_w = getattr(parent, 'winfo_toplevel', lambda: parent)()
        try:
            win.geometry('+%d+%d' % (parent_w.winfo_rootx()+50, parent_w.winfo_rooty()+50))
        except Exception:
            pass

        win.wait_window()
        return sel_vals

    # ask counters first so user sees selection
    try:
        sel_counters = _ask_select_counters(parent, db_path)
    except Exception:
        sel_counters = None

    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    params = ()
    if sel_counters:
        placeholders = ','.join('?' for _ in sel_counters)
        sql = f"""
    SELECT 
        ic.counter_name,
        d.deposit_description AS deposito,
        r.rack_description AS rack,
        ic.location AS ubicacion,
        ic.code_item AS producto_codigo,
        COALESCE(i.description_item, '') AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total
    FROM inventory_count ic
    LEFT JOIN deposits d ON ic.deposit_id = d.deposit_id
    LEFT JOIN racks r ON ic.rack_id = r.rack_id
    LEFT JOIN items i on ic.code_item = i.code_item
    WHERE ic.counter_name IN ({placeholders})
    ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;
    """
        params = tuple(sel_counters)
    else:
        sql = """
    SELECT 
        ic.counter_name,
        d.deposit_description AS deposito,
        r.rack_description AS rack,
        ic.location AS ubicacion,
        ic.code_item AS producto_codigo,
        COALESCE(i.description_item, '') AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total
    FROM inventory_count ic
    LEFT JOIN deposits d ON ic.deposit_id = d.deposit_id
    LEFT JOIN racks r ON ic.rack_id = r.rack_id
    LEFT JOIN items i on ic.code_item = i.code_item
    ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;
    """

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    grouped = {}
    for row in rows:
        counter_name, deposito, rack = row[0], row[1], row[2]
        grouped.setdefault(counter_name, {}).setdefault(deposito, {}).setdefault(rack, []).append(row)

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    contador_style = styles["Heading2"]
    deposito_style = styles["Heading3"]
    rack_style = styles["Heading4"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte por Contador", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["Ubicación", "Código", "Producto", "Cajas", "U/caja", "Tot. U/cajas", "Sueltos", "Total"]
    for ci, (counter_name, depositos) in enumerate(grouped.items()):
        story.append(Paragraph(f"Contador: {counter_name}", contador_style))
        story.append(Spacer(1, 6))
        for deposito, racks in depositos.items():
            story.append(Paragraph(f"Depósito: {deposito}", deposito_style))
            story.append(Spacer(1, 4))
            for rack, items in racks.items():
                story.append(Paragraph(f"Rack: {rack} — {len(items)} registros", rack_style))
                story.append(Spacer(1, 4))
                data = [col_headers]
                for r in items:
                    data.append([
                        r[3] or "",
                        r[4] or "",
                        (r[5] or "")[:60],
                        str(r[6] or 0),
                        str(r[7] or 0),
                        str(r[8] or 0),
                        str(r[9] or 0),
                        str(r[10] or 0)
                    ])
                table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[90, 60, 140, 35, 40, 45, 45, 45])
                tbl_style = TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ])
                try:
                    hdrs = data[0] if data else []
                    numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
                    ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                    for i in ncols:
                        try:
                            tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                        except Exception:
                            pass
                except Exception:
                    pass
                table.setStyle(tbl_style)
                story.append(table)
                story.append(Spacer(1, 8))
    
    if not grouped:
        story.append(Paragraph("No hay registros para reportar.", normal))

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_diferencias_resumen(parent, db_path: str = DEFAULT_DB):
    """Generate a PDF from `inventory_count_res` showing key columns and absolute difference.

    Columns shown: code_item, description_item, total, sales_qty, purchasing_qty, total_calc, |difference|.
    Orders rows by absolute difference descending.
    """
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(inventory_count_res)")
        cols = [c[1] for c in cur.fetchall()]

        sel_cols = ['code_item']
        sel_cols.append('description_item' if 'description_item' in cols else "'' AS description_item")
        sel_cols.append('total' if 'total' in cols else '0 AS total')
        sel_cols.append('sales_qty' if 'sales_qty' in cols else '0 AS sales_qty')
        sel_cols.append('purchasing_qty' if 'purchasing_qty' in cols else '0 AS purchasing_qty')
        sel_cols.append('total_calc' if 'total_calc' in cols else '0 AS total_calc')

        if 'difference' in cols:
            diff_expr = 'difference'
        elif 'total_calc' in cols and 'current_inventory' in cols:
            diff_expr = '(current_inventory - total_calc)'
        elif 'total' in cols and 'current_inventory' in cols:
            diff_expr = '(current_inventory - total)'
        else:
            diff_expr = '0'

        sql = f"SELECT {', '.join(sel_cols)}, {diff_expr} AS difference FROM inventory_count_res ORDER BY ABS({diff_expr}) DESC"
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal = styles['Normal']

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph('Reporte Diferencias - Resumen (inventory_count_res)', title_style))
    story.append(Spacer(1, 8))

    headers = ['Código', 'Descripción', 'Total', 'Sales', 'Purchasing', 'Total_calc', 'Diferencia']
    data = [headers]
    for r in rows:
        def _fmt_int(x):
            try:
                n = int(round(float(x)))
            except Exception:
                try:
                    n = int(x)
                except Exception:
                    n = 0
            return f"{n:,}".replace(",", ".")

        data.append([
            r[0] or '',
            (r[1] or '')[:200],
            _fmt_int(r[2]),
            _fmt_int(r[3]),
            _fmt_int(r[4]),
            _fmt_int(r[5]),
            _fmt_int(abs(r[6] or 0))
        ])

    if len(data) == 1:
        story.append(Paragraph('No hay registros para reportar.', normal))
    else:
        table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=[80, 360, 60, 60, 60, 60, 60])
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
        try:
            hdrs = data[0] if data else []
            numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
            ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
            for i in ncols:
                try:
                    tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                except Exception:
                    pass
        except Exception:
            pass
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror('Error', f'Error al generar el PDF: {e}', parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo('OK', f'Reporte PDF generado: {file_path}', parent=parent)
    


def generate_pdf_report_por_deposito(parent, db_path: str = DEFAULT_DB):
    # Ask which deposits to include (use resumen helper if available)
    sel_deps = None
    try:
        try:
            from ui_pdf_report_resumen import _ask_select_deposits
            sel_deps = _ask_select_deposits(parent, db_path)
        except Exception:
            # helper not available; ignore and continue with all deposits
            sel_deps = None
    except Exception:
        sel_deps = None

    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    # Build SQL, optionally filtering by selected deposits
    base_sql = """
    SELECT 
        d.deposit_description AS deposito,
        r.rack_description AS rack,
        ic.location AS ubicacion,
        ic.code_item AS producto_codigo,
        COALESCE(i.description_item, '') AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total,
        ic.deposit_id AS deposit_id
    FROM inventory_count ic
    LEFT JOIN deposits d ON ic.deposit_id = d.deposit_id
    LEFT JOIN racks r ON ic.rack_id = r.rack_id
    LEFT JOIN items i on ic.code_item = i.code_item
    """

    params = ()
    if sel_deps:
        placeholders = ','.join('?' for _ in sel_deps)
        sql = base_sql + f" WHERE ic.deposit_id IN ({placeholders}) ORDER BY d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;"
        params = tuple(sel_deps)
    else:
        sql = base_sql + " ORDER BY d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;"

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    grouped = {}
    for row in rows:
        deposito, rack = row[0], row[1]
        grouped.setdefault(deposito, {}).setdefault(rack, []).append(row)

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    deposito_style = styles["Heading2"]
    rack_style = styles["Heading3"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte por Depósito", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["Ubicación", "Código", "Producto", "Cajas", "U/caja", "Tot. U/cajas", "Sueltos", "Total"]
    for di, (deposito, racks) in enumerate(grouped.items()):
        story.append(Paragraph(f"Depósito: {deposito}", deposito_style))
        story.append(Spacer(1, 6))
        for rack, items in racks.items():
            story.append(Paragraph(f"Rack: {rack} — {len(items)} registros", rack_style))
            story.append(Spacer(1, 4))
            data = [col_headers]
            for r in items:
                data.append([
                    r[2] or "",
                    r[3] or "",
                    (r[4] or "")[:60],
                    str(r[5] or 0),
                    str(r[6] or 0),
                    str(r[7] or 0),
                    str(r[8] or 0),
                    str(r[9] or 0)
                ])
            table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[90, 60, 140, 35, 40, 45, 45, 45])
            tbl_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
            try:
                hdrs = data[0] if data else []
                numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
                ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                for i in ncols:
                    try:
                        tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                    except Exception:
                        pass
            except Exception:
                pass
            table.setStyle(tbl_style)
            story.append(table)
            story.append(Spacer(1, 8))
        if di < len(grouped) - 1:
            story.append(PageBreak())

    if not grouped:
        story.append(Paragraph("No hay registros para reportar.", normal))

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_verificacion(parent, db_path: str = DEFAULT_DB):
    # Ask which counters to include (multi-select), similar to `generate_pdf_report_por_contador`.
    def _ask_select_counters(parent, db_path: str):
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception:
            return None

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT COALESCE(counter_name, '') FROM inventory_count ORDER BY 1")
            counters = [c[0] for c in cur.fetchall() if c is not None]
            conn.close()
        except Exception:
            return None

        if not counters:
            return None

        win = tk.Toplevel(parent)
        win.title('Seleccionar Contadores')
        win.transient(parent)
        win.grab_set()

        lbl = ttk.Label(win, text='Seleccione contadores (marca "Todos" o elija individualmente):')
        lbl.pack(padx=8, pady=(8, 4))

        canvas = tk.Canvas(win, borderwidth=0, height=200)
        frame_inner = ttk.Frame(canvas)
        vsb = ttk.Scrollbar(win, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True, padx=8, pady=4)
        canvas.create_window((0, 0), window=frame_inner, anchor='nw')

        def _on_frame_configure(event=None):
            try:
                canvas.configure(scrollregion=canvas.bbox('all'))
            except Exception:
                pass

        frame_inner.bind('<Configure>', _on_frame_configure)

        vars_list = []
        id_map = []
        todos_var = tk.IntVar(value=1)

        def _set_all(v=None):
            val = todos_var.get()
            for vv in vars_list:
                vv.set(bool(val))

        chk_all = ttk.Checkbutton(frame_inner, text='Todos', variable=todos_var, command=_set_all)
        chk_all.pack(anchor='w', pady=2)

        for c in counters:
            cname = c or ''
            var = tk.IntVar(value=1)
            cb = ttk.Checkbutton(frame_inner, text=cname if cname != '' else '(Sin nombre)', variable=var, onvalue=1, offvalue=0)
            cb.pack(anchor='w', padx=6)
            vars_list.append(var)
            id_map.append(cname)

        def _update_todos():
            try:
                all_on = all(v.get() for v in vars_list)
                todos_var.set(1 if all_on else 0)
            except Exception:
                pass

        for var in vars_list:
            try:
                var.trace_add('write', lambda *a: _update_todos())
            except Exception:
                try:
                    var.trace('w', lambda *a: _update_todos())
                except Exception:
                    pass

        sel_vals = None
        frm = ttk.Frame(win)
        frm.pack(padx=8, pady=8)

        def _on_ok():
            selected = [id_map[i] for i, v in enumerate(vars_list) if v.get()]
            nonlocal sel_vals
            sel_vals = selected if selected else None
            win.destroy()

        def _on_cancel():
            nonlocal sel_vals
            sel_vals = None
            win.destroy()

        btn_ok = ttk.Button(frm, text='OK', command=_on_ok)
        btn_ok.pack(side='left', padx=6)
        btn_cancel = ttk.Button(frm, text='Cancelar', command=_on_cancel)
        btn_cancel.pack(side='left', padx=6)

        parent_w = getattr(parent, 'winfo_toplevel', lambda: parent)()
        try:
            win.geometry('+%d+%d' % (parent_w.winfo_rootx()+50, parent_w.winfo_rooty()+50))
        except Exception:
            pass

        win.wait_window()
        return sel_vals

    try:
        sel_counters = _ask_select_counters(parent, db_path)
    except Exception:
        sel_counters = None

    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    params = ()
    sql = """
    SELECT 
        ic.counter_name,
        d.deposit_description AS deposito,
        r.rack_description AS rack,
        ic.location AS ubicacion,
        ic.code_item AS producto_codigo,
        COALESCE(i.description_item, '') AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total,
        ic.id,
        ic.remarks
    FROM inventory_count ic
    LEFT JOIN deposits d ON ic.deposit_id = d.deposit_id
    LEFT JOIN racks r ON ic.rack_id = r.rack_id
    LEFT JOIN items i on ic.code_item = i.code_item
    """

    if sel_counters:
        placeholders = ','.join('?' for _ in sel_counters)
        sql = sql + f"\nWHERE ic.counter_name IN ({placeholders})\nORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.id ASC;"
        params = tuple(sel_counters)
    else:
        sql = sql + " ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.id ASC;"

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    grouped = {}
    for row in rows:
        counter_name, deposito, rack = row[0], row[1], row[2]
        grouped.setdefault(counter_name, {}).setdefault(deposito, {}).setdefault(rack, []).append(row)

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    contador_style = styles["Heading2"]
    deposito_style = styles["Heading3"]
    rack_style = styles["Heading4"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte Verificación (orden por id)", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["Ubicación", "Código", "Producto", "Cajas", "U/caja", "Tot. U/cajas", "Sueltos", "Total", "ID", "Comentarios"]
    for ci, (counter_name, depositos) in enumerate(grouped.items()):
        story.append(Paragraph(f"Contador: {counter_name}", contador_style))
        story.append(Spacer(1, 6))
        for deposito, racks in depositos.items():
            story.append(Paragraph(f"Depósito: {deposito}", deposito_style))
            story.append(Spacer(1, 4))
            for rack, items in racks.items():
                story.append(Paragraph(f"Rack: {rack} — {len(items)} registros", rack_style))
                story.append(Spacer(1, 4))
                data = [col_headers]
                for r in items:
                    data.append([
                        r[3] or "",
                        r[4] or "",
                        (r[5] or "")[:60],
                        str(r[6] or 0),
                        str(r[7] or 0),
                        str(r[8] or 0),
                        str(r[9] or 0),
                        str(r[10] or 0),
                        str(r[11] or ""),
                        (r[12] or "")[:120]
                    ])
                table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[90, 60, 140, 35, 40, 45, 45, 45, 30, 120])
                tbl_style = TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ])
                try:
                    hdrs = data[0] if data else []
                    numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
                    ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                    for i in ncols:
                        try:
                            tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                        except Exception:
                            pass
                except Exception:
                    pass
                table.setStyle(tbl_style)
                story.append(table)
                story.append(Spacer(1, 8))
        if ci < len(grouped) - 1:
            story.append(PageBreak())

    if not grouped:
        story.append(Paragraph("No hay registros para reportar.", normal))

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}")

"""
ui_pdf_report.py

Provides a utility to add a "PDF Report" button to an existing Tkinter frame.
The button generates a PDF report of inventory_count joined with items, deposits and racks,
grouped by deposit and rack, inserting a page break for each deposit.

Usage:
    from ui_pdf_report import add_pdf_report_button
    add_pdf_report_button(frm, db_path="inventariovlm.db")

Dependencies:
    reportlab (pip install reportlab)
"""
DEFAULT_DB = "inventariovlm.db"
import sqlite3
import os
import sys
import subprocess
from tkinter import filedialog, messagebox
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def _open_pdf_file(file_path, parent=None):
    """Try to open the generated PDF using a platform-appropriate opener.

    Swallows errors (doesn't crash the app). If a parent tkinter widget is
    provided and opening fails, shows a warning messagebox so the user can
    attempt to open the file manually.
    """
    try:
        if os.name == 'nt':
            os.startfile(file_path)
            return True
        # macOS
        if sys.platform == 'darwin':
            subprocess.Popen(['open', file_path])
            return True
        # Linux / other
        subprocess.Popen(['xdg-open', file_path])
        return True
    except Exception as e:
        try:
            if parent is not None:
                messagebox.showwarning("Aviso", f"No se pudo abrir el PDF automáticamente: {e}\nArchivo generado: {file_path}", parent=parent)
        except Exception:
            # If messagebox also fails, silently ignore
            pass
        return False

def add_pdf_report_button(parent_frame, db_path=DEFAULT_DB, button_text="Generar PDF"):
    """
    Adds a button to parent_frame that opens a save dialog and generates the PDF report
    from the given sqlite db_path.
    """
    try:
        from tkinter import ttk
    except Exception:
        # fallback to tk.Button if ttk not available (very unlikely)
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report(parent_frame, db_path))
        btn.grid(row=23, column=0, pady=8)
        return btn

    btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report(parent_frame, db_path))
    # place by default at row 23 col 0; callers can re-grid if needed
    try:
        btn.grid(row=23, column=0, pady=8)
    except Exception:
        # if grid not appropriate, pack
        btn.pack(pady=8)
    return btn


def _invoke_report_by_name(func_name: str, parent: object, db_path: str):
    """Import the ui_pdf_report module and invoke a report function by name.

    Shows an error message if the function is not found or call fails.
    """
    try:
        mod = __import__(__name__)
        fn = getattr(mod, func_name, None)
        if fn is None:
            messagebox.showerror("Error", f"No se encontró la función de reporte: {func_name}", parent=parent)
            return
        return fn(parent, db_path=db_path)
    except Exception as e:
        messagebox.showerror("Error", f"Error al ejecutar el reporte {func_name}: {e}", parent=parent)
        return

def generate_pdf_report(parent, db_path=DEFAULT_DB):
    """
    Query the database and build a PDF grouped by deposit and rack with a page break per deposit.
    """
    # Ask file destination
    file_path = filedialog.asksaveasfilename(parent=parent, defaultextension=".pdf",
                                             filetypes=[("PDF files", "*.pdf")])
    if not file_path:
        return

    # Ensure reportlab is available
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
    except Exception as e:
        messagebox.showerror("Error", "No se encontró 'reportlab'. Instala reportlab (ej: pip install reportlab).")
        return

    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}")
        return

    # Query rows ordered by deposit and rack so grouping is straightforward
    sql = """
        SELECT c.id, c.counter_name, c.code_item,
               COALESCE(i.description_item, '') AS description_item,
               c.boxqty, c.boxunitqty, c.boxunittotal,
               c.magazijn, c.winkel, c.total, c.current_inventory, c.difference,
               COALESCE(d.deposit_description, '') AS deposit_name,
               COALESCE(r.rack_description, '') AS rack_name,
               c.location, c.count_date
        FROM inventory_count c
        LEFT JOIN items i ON i.code_item = c.code_item
        LEFT JOIN deposits d ON d.deposit_id = c.deposit_id
        LEFT JOIN racks r ON r.rack_id = c.rack_id
        ORDER BY deposit_name, rack_name, c.count_date, c.counter_name, c.code_item
    """

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}")
        return

    # Build structure grouped by deposit -> rack -> rows
    grouped = []
    current_deposit = None
    current_rack = None
    deposit_block = None
    for row in rows:
        deposit_name = row[12] or "Sin depósito"
        rack_name = row[13] or "Sin rack"
        if deposit_name != current_deposit:
            # start new deposit block
            deposit_block = {"deposit": deposit_name, "racks": {}}
            grouped.append(deposit_block)
            current_deposit = deposit_name
            current_rack = None
        if rack_name != current_rack:
            deposit_block["racks"][rack_name] = []
            current_rack = rack_name
        deposit_block["racks"][rack_name].append(row)

    # Prepare PDF flowables
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    deposit_style = styles["Heading2"]
    rack_style = styles["Heading3"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []

    # Title
    story.append(Paragraph("Reporte de Inventario", title_style))
    story.append(Spacer(1, 8))

    # Table column headers
    col_headers = ["ID", "Contador", "Código", "Descripción", "Cajas", "U/caja", "Total cajas", "Magazijn", "Winkel", "Total", "Actual", "Difer.", "Ubicación", "Fecha"]

    # For each deposit: add header, iterate racks, add tables; page break after deposit
    for di, deposit_block in enumerate(grouped):
        story.append(Paragraph(f"Depósito: {deposit_block['deposit']}", deposit_style))
        story.append(Spacer(1, 6))
        for rack_name, items in deposit_block["racks"].items():
            story.append(Paragraph(f"Rack: {rack_name} — {len(items)} registros", rack_style))
            story.append(Spacer(1, 4))
            # Build table data (header + rows)
            data = [col_headers]
            for r in items:
                # r indexes from SELECT: see sql above
                data.append([
                    r[0] or "",
                    r[1] or "",
                    r[2] or "",
                    (r[3] or "")[:60],
                    _fmt_int(r[4] or 0),
                    _fmt_int(r[5] or 0),
                    _fmt_int(r[6] or 0),
                    _fmt_int(r[7] or 0),
                    _fmt_int(r[8] or 0),
                    _fmt_int(r[9] or 0),
                    _fmt_int(r[10] or 0),
                    _fmt_int(r[11] or 0),
                    r[14] or "",
                    r[15] or ""
                ])
            # Create table and style it
            table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[30, 70, 60, 140, 35, 40, 45, 45, 40, 45, 40, 40, 90, 60])
            tbl_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
            try:
                hdrs = data[0] if data else []
                numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
                ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                for i in ncols:
                    try:
                        tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                    except Exception:
                        pass
            except Exception:
                pass
            table.setStyle(tbl_style)
            story.append(table)
            story.append(Spacer(1, 8))
        # Page break after each deposit except last
        if di < len(grouped) - 1:
            story.append(PageBreak())

    # If no rows, add a paragraph
    if not grouped:
        story.append(Paragraph("No hay registros para reportar.", normal))

    # Build PDF
    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}")
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}")


def generate_pdf_report_diferencias(parent, db_path: str = DEFAULT_DB):
    """Genera un reporte con las diferencias por item y ubicación.

    Usa la consulta proporcionada por el usuario, agrupando por `ic.code_item, ic.location`.
    """
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    sql = '''
    select ic.code_item item,
           ic.location ubicacion, 
           max(i.description_item) item_descripcion, 
           sum(ic.boxunittotal) en_cajas, 
           sum(ic.magazijn) sueltos, 
           sum(ic.total) total, 
           max(i.current_inventory) inventario_actual,
           SUM(ic.total) - MAX(i.current_inventory) AS diferencia
      from inventory_count ic
      left join items i on i.code_item = ic.code_item
      left join racks r on r.rack_id = ic.rack_id
      left join deposits d on d.deposit_id = ic.deposit_id
     group by ic.code_item, ic.location
     ORDER BY ic.code_item ASC, ic.location ASC
    '''

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    # Build PDF
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except Exception:
        messagebox.showerror("Error", "No se encontró 'reportlab'. Instala reportlab (ej: pip install reportlab).", parent=parent)
        return

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte de Diferencias por Item y Ubicación", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["Código", "Ubicación", "Descripción", "En Cajas", "Sueltos", "Total", "Inventario Actual", "Diferencia"]
    data = [col_headers]
    for r in rows:
        # r corresponds to select order: item, ubicacion, item_descripcion, en_cajas, sueltos, total, inventario_actual, diferencia
        data.append([
            r[0] or "",
            r[1] or "",
            (r[2] or "")[:80],
            _fmt_int(r[3] or 0),
            _fmt_int(r[4] or 0),
            _fmt_int(r[5] or 0),
            _fmt_int(r[6] or 0),
            _fmt_int(r[7] or 0),
        ])

    # Table column widths tuned for landscape A4
    colWidths = [70, 120, 240, 50, 50, 60, 70, 60]
    table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=colWidths)
    tbl_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])
    try:
        hdrs = data[0] if data else []
        numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
        ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
        for i in ncols:
            try:
                tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
            except Exception:
                pass
    except Exception:
        pass
    table.setStyle(tbl_style)
    story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_verificacion(parent, db_path=DEFAULT_DB):
    """
    Genera un PDF similar a 'por contador' pero dentro de cada grupo ordena los detalles por id (orden de inserción).
    """
    file_path = filedialog.asksaveasfilename(parent=parent, defaultextension=".pdf",
                                             filetypes=[("PDF files", "*.pdf")])
    if not file_path:
        return
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
    except Exception:
        messagebox.showerror("Error", "No se encontró 'reportlab'. Instala reportlab (ej: pip install reportlab).")
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}")
        return
    sql = '''
    SELECT 
        ic.counter_name,
        d.deposit_description AS deposito,
        r.rack_description AS rack,
        ic.location AS ubicacion,
        ic.code_item AS producto_codigo,
        COALESCE(i.description_item, '') AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total,
        ic.id,
        ic.remarks
    FROM inventory_count ic
    LEFT JOIN deposits d ON ic.deposit_id = d.deposit_id
    LEFT JOIN racks r ON ic.rack_id = r.rack_id
    LEFT JOIN items i on ic.code_item = i.code_item
    ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.id ASC;
    '''
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}")
        return
    # Agrupar por counter_name, depósito y rack
    grouped = {}
    for row in rows:
        counter_name, deposito, rack = row[0], row[1], row[2]
        if counter_name not in grouped:
            grouped[counter_name] = {}
        if deposito not in grouped[counter_name]:
            grouped[counter_name][deposito] = {}
        if rack not in grouped[counter_name][deposito]:
            grouped[counter_name][deposito][rack] = []
        grouped[counter_name][deposito][rack].append(row)
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    contador_style = styles["Heading2"]
    deposito_style = styles["Heading3"]
    rack_style = styles["Heading4"]
    normal = styles["Normal"]
    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte Verificación (orden por id)", title_style))
    story.append(Spacer(1, 8))
    col_headers = ["Ubicación", "Código", "Producto", "Cajas", "U/caja", "Tot. U/cajas", "Sueltos", "Total", "ID", "Comentarios"]
    for ci, (counter_name, depositos) in enumerate(grouped.items()):
        story.append(Paragraph(f"Contador: {counter_name}", contador_style))
        story.append(Spacer(1, 6))
        for di, (deposito, racks) in enumerate(depositos.items()):
            story.append(Paragraph(f"Depósito: {deposito}", deposito_style))
            story.append(Spacer(1, 4))
            for rack, items in racks.items():
                story.append(Paragraph(f"Rack: {rack} — {len(items)} registros", rack_style))
                story.append(Spacer(1, 4))
                data = [col_headers]
                for r in items:
                    # r contains fields as selected above, with remarks at the end
                    data.append([
                            r[3] or "",
                            r[4] or "",
                            (r[5] or "")[:60],
                            _fmt_int(r[6] or 0),
                            _fmt_int(r[7] or 0),
                            _fmt_int(r[8] or 0),
                            _fmt_int(r[9] or 0),
                            _fmt_int(r[10] or 0),
                            str(r[11] or ""),
                            (r[12] or "")[:120]
                        ])
                    table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[90, 60, 140, 35, 40, 45, 45, 45, 30, 120])
                    tbl_style = TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ])
                    try:
                        hdrs = data[0] if data else []
                        numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot', 'dif', 'difer', 'difference')
                        ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                        for i in ncols:
                            try:
                                tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                            except Exception:
                                pass
                    except Exception:
                        pass
                    table.setStyle(tbl_style)
                story.append(table)
                story.append(Spacer(1, 8))
        if ci < len(grouped) - 1:
            story.append(PageBreak())
    if not grouped:
        story.append(Paragraph("No hay registros para reportar.", normal))
    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}")
        return
    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}")


def generate_pdf_report_diferencias_por_item(parent, db_path: str = DEFAULT_DB):
    """Generate a PDF that aggregates differences grouped by `code_item`.

    The report contains one row per item with summed `total`, `current_inventory` and `difference`.
    """
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    sql = """
    SELECT ic.code_item AS item,
           MAX(i.description_item) AS item_descripcion,
           SUM(ic.boxunittotal) AS en_cajas,
           SUM(ic.magazijn) AS sueltos,
           SUM(ic.total) AS total,
           MAX(i.current_inventory) AS inventario_actual,
           SUM(ic.total) - MAX(i.current_inventory) AS diferencia
      FROM inventory_count ic
      LEFT JOIN items i ON i.code_item = ic.code_item
     GROUP BY ic.code_item
     ORDER BY ic.code_item ASC;
    """

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    # lazy imports
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph("Reporte de Diferencias por Item", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["Código", "Descripción", "En Cajas", "Sueltos", "Total", "Actual", "Diferencia"]
    data = [col_headers]
    for r in rows:
        data.append([
            r[0] or "",
            (r[1] or "")[:140],
            str(r[2] or 0),
            str(r[3] or 0),
            str(r[4] or 0),
            str(r[5] or 0),
            str(r[6] or 0)
        ])

    if len(data) == 1:
        story.append(Paragraph("No hay registros para reportar.", normal))
    else:
        table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[70, 300, 60, 60, 60, 60, 60])
        tbl_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_diferencias_item_detalle(parent, db_path: str = DEFAULT_DB):
    """Generate a PDF for a single item (asked from user) showing differences grouped
    by `counter_name` and `location`. The user is prompted for the `code_item`.
    """
    try:
        from tkinter import simpledialog
    except Exception:
        simpledialog = None

    if simpledialog is None:
        messagebox.showerror("Error", "No se puede pedir el parámetro al usuario (simpledialog no disponible).", parent=parent)
        return

    item_code = simpledialog.askstring("Código de Item", "Ingrese el código del item:", parent=parent)
    if not item_code:
        return

    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    sql = '''
    SELECT ic.counter_name AS counter,
           ic.location AS ubicacion,
           SUM(ic.boxunittotal) AS en_cajas,
           SUM(ic.magazijn) AS sueltos,
           SUM(ic.total) AS total,
           MAX(i.current_inventory) AS inventario_actual,
           SUM(ic.total) - MAX(i.current_inventory) AS diferencia,
           MAX(i.description_item) AS descripcion
      FROM inventory_count ic
      LEFT JOIN items i ON i.code_item = ic.code_item
     WHERE ic.code_item = ?
     GROUP BY ic.counter_name, ic.location
     ORDER BY ic.counter_name ASC, ABS(diferencia) DESC;
    '''

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, (item_code,))
        rows = cur.fetchall()
        # try to fetch item description from first row if present
        item_desc = rows[0][7] if rows else None
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    # lazy imports for reportlab
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles.get("Heading3", styles["Heading2"])
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    title = f"Reporte Detallado de Diferencias para Item {item_code}"
    if item_desc:
        title += f" — {item_desc}"
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 8))

    if not rows:
        story.append(Paragraph("No hay registros para ese código de item.", normal))
    else:
        # group rows by counter
        grouped = {}
        for r in rows:
            counter = r[0] or ""
            location = (r[1] or "")[:200]
            entry = {
                "en_cajas": r[2] or 0,
                "sueltos": r[3] or 0,
                "total": r[4] or 0,
                "actual": r[5] or 0,
                "diferencia": r[6] or 0,
            }
            grouped.setdefault(counter, []).append((location, entry))

        # iterate counters
        for ci, counter in enumerate(sorted(grouped.keys())):
            story.append(Paragraph(f"Contador: {counter}", subtitle_style))
            story.append(Spacer(1, 6))

            # Build table per counter with locations as rows
            col_headers = ["Ubicación", "En Cajas", "Sueltos", "Total", "Actual", "Diferencia"]
            data = [col_headers]
            items = grouped[counter]
            # sort by absolute diferencia
            items = sorted(items, key=lambda x: abs(x[1].get("diferencia", 0)), reverse=True)
            for loc, it in items:
                data.append([
                    loc,
                    _fmt_int(it.get("en_cajas", 0)),
                    _fmt_int(it.get("sueltos", 0)),
                    _fmt_int(it.get("total", 0)),
                    _fmt_int(it.get("actual", 0)),
                    _fmt_int(it.get("diferencia", 0)) if it.get("diferencia") is not None else "",
                ])

            table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[300, 60, 60, 60, 60, 60])
            tbl_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
            try:
                hdrs = data[0] if data else []
                numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot')
                ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                for i in ncols:
                    try:
                        tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                    except Exception:
                        pass
            except Exception:
                pass
            table.setStyle(tbl_style)
            story.append(table)
            story.append(Spacer(1, 8))

            if ci != len(grouped) - 1:
                story.append(PageBreak())

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def add_pdf_report_diferencias_por_item_detalle_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = "Diferencias Item Detalle"):
    return _make_button(parent_frame, row=30, text=button_text, command=lambda: generate_pdf_report_diferencias_item_detalle(parent_frame, db_path))

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_diferencias_threshold(parent, db_path: str = DEFAULT_DB):
    """Prompt for a threshold and generate a PDF with items whose absolute difference
    (SUM(total) - MAX(current_inventory)) is greater than the given threshold.
    """
    try:
        from tkinter import simpledialog
    except Exception:
        simpledialog = None

    if simpledialog is None:
        messagebox.showerror("Error", "No se puede pedir el parámetro al usuario (simpledialog no disponible).", parent=parent)
        return

    thr = simpledialog.askinteger("Umbral", "Mostrar diferencias con valor absoluto mayor que:", parent=parent, minvalue=0)
    if thr is None:
        return

    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    sql = """
    SELECT ic.code_item AS item,
           MAX(i.description_item) AS item_descripcion,
           SUM(ic.boxunittotal) AS en_cajas,
           SUM(ic.magazijn) AS sueltos,
           SUM(ic.total) AS total,
           MAX(i.current_inventory) AS inventario_actual,
           SUM(ic.total) - MAX(i.current_inventory) AS diferencia
      FROM inventory_count ic
      LEFT JOIN items i ON i.code_item = ic.code_item
     GROUP BY ic.code_item
    HAVING ABS(SUM(ic.total) - MAX(i.current_inventory)) > ?
    ORDER BY ABS(SUM(ic.total) - MAX(i.current_inventory)) DESC, ic.code_item ASC;
    """

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, (thr,))
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    # lazy imports
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph(f"Reporte de Diferencias por Item (|diferencia| > {thr})", title_style))
    story.append(Spacer(1, 8))

    col_headers = ["Código", "Descripción", "En Cajas", "Sueltos", "Total", "Actual", "Diferencia"]
    data = [col_headers]
    for r in rows:
        data.append([
            r[0] or "",
            (r[1] or "")[:140],
            str(r[2] or 0),
            str(r[3] or 0),
            str(r[4] or 0),
            str(r[5] or 0),
            str(r[6] or 0)
        ])

    if len(data) == 1:
        story.append(Paragraph("No hay registros que cumplan el umbral especificado.", normal))
    else:
        table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[70, 300, 60, 60, 60, 60, 60])
        tbl_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)


def generate_pdf_report_diferencias_por_counter(parent, db_path: str = DEFAULT_DB):
    """Generate report grouped by counter_name, location and item using the provided SQL.
    Filters differences between 20 and 100 (as in the supplied query).
    """
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    # ask user for absolute-difference range
    try:
        from tkinter import simpledialog
    except Exception:
        simpledialog = None

    if simpledialog is None:
        messagebox.showerror("Error", "No se puede pedir el parámetro al usuario (simpledialog no disponible).", parent=parent)
        return

    minv = simpledialog.askinteger("Rango mínimo", "Valor mínimo de |diferencia|:", parent=parent, minvalue=0)
    if minv is None:
        return
    maxv = simpledialog.askinteger("Rango máximo", "Valor máximo de |diferencia|:", parent=parent, minvalue=minv)
    if maxv is None:
        return

    sql = '''
SELECT 
       ic.counter_name AS counter,
       ic.location AS ubicacion, 
       ic.code_item AS item,
       MAX(i.description_item) AS item_descripcion, 
       SUM(boxunittotal) AS en_cajas, 
       SUM(ic.magazijn) AS sueltos, 
       SUM(ic.total) AS total, 
       MAX(i.current_inventory) AS inventario_actual,
       SUM(ic.total) - MAX(i.current_inventory) AS diferencia
FROM inventory_count ic
JOIN items i      ON i.code_item = ic.code_item
JOIN racks r      ON r.rack_id = ic.rack_id
JOIN deposits d   ON d.deposit_id = ic.deposit_id
GROUP BY ic.code_item, ic.counter_name, ic.location
HAVING ABS(SUM(ic.total) - MAX(i.current_inventory)) BETWEEN ? AND ?
ORDER BY ABS(diferencia) DESC;
'''

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, (minv, maxv))
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer la base de datos: {e}", parent=parent)
        return

    # PDF build - group by counter -> location -> items; page break per counter
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles.get("Heading3", styles["Heading2"])
    normal = styles["Normal"]

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph(f"Reporte Diferencias por Contador / Ubicación / Item (|diferencia| entre {minv} y {maxv})", title_style))
    story.append(Spacer(1, 8))

    if not rows:
        story.append(Paragraph("No hay registros que cumplan el filtro.", normal))
    else:
        # organize rows into nested dict: counter -> location -> list(rows)
        grouped = {}
        for r in rows:
            counter = r[0] or ""
            location = (r[1] or "")[:200]
            entry = {
                "code": r[2] or "",
                "description": (r[3] or "")[:200],
                "encajas": r[4] or 0,
                "sueltos": r[5] or 0,
                "total": r[6] or 0,
                "actual": r[7] or 0,
                "diferencia": r[8] or 0,
            }
            grouped.setdefault(counter, {}).setdefault(location, []).append(entry)

        # iterate counters in sorted order
        counters = list(grouped.keys())
        for ci, counter in enumerate(counters):
            # add counter header
            story.append(Paragraph(f"Contador: {counter}", subtitle_style))
            story.append(Spacer(1, 6))

            locations = list(grouped[counter].keys())
            for location in locations:
                story.append(Paragraph(f"Ubicación: {location}", styles.get("Heading4", normal)))
                story.append(Spacer(1, 4))

                # table headers
                col_headers = ["Código", "Descripción", "En Cajas", "Sueltos", "Total", "Actual", "Diferencia"]
                data = [col_headers]
                # sort items by absolute diferencia desc
                items = sorted(grouped[counter][location], key=lambda x: abs(x.get("diferencia", 0)), reverse=True)
                for it in items:
                    data.append([
                        it["code"],
                        it["description"],
                        _fmt_int(it.get("encajas", 0)),
                        _fmt_int(it.get("sueltos", 0)),
                        _fmt_int(it.get("total", 0)),
                        _fmt_int(it.get("actual", 0)),
                        _fmt_int(it.get("diferencia", 0)) if it.get("diferencia") is not None else "",
                    ])

                table = Table(data, repeatRows=1, hAlign="LEFT", colWidths=[80, 340, 50, 50, 60, 60, 60])
                tbl_style = TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ])
                try:
                    hdrs = data[0] if data else []
                    numeric_keys = ('total', 'caja', 'cajas', 'inventario', 'actual', 'sueltos', 'sales', 'purchas', 'qty', 'cant', 'magazijn', 'winkel', 'tot')
                    ncols = [i for i, h in enumerate(hdrs) if any(k in str(h).lower() for k in numeric_keys)]
                    for i in ncols:
                        try:
                            tbl_style.add('ALIGN', (i, 1), (i, -1), 'RIGHT')
                        except Exception:
                            pass
                except Exception:
                    pass
                table.setStyle(tbl_style)
                story.append(table)
                story.append(Spacer(1, 8))

            # add a page break between counters except after last
            if ci != len(counters) - 1:
                story.append(PageBreak())

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror("Error", f"Error al generar el PDF: {e}", parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}", parent=parent)