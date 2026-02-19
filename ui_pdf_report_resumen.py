import os
import sqlite3
from typing import Optional
from tkinter import filedialog, messagebox

DEFAULT_DB = "inventariovlm.db"

print('DEBUG: ui_pdf_report_resumen module loaded')


def _asksave(parent: Optional[object], default_name: Optional[str] = None) -> Optional[str]:
    try:
        # determine suggested filename: explicit default_name or parent's selected report name
        suggested = default_name
        try:
            if suggested is None and hasattr(parent, '_selected_report_name'):
                suggested = getattr(parent, '_selected_report_name')
        except Exception:
            suggested = suggested
        if suggested:
            # sanitize: keep short filename, replace spaces with underscores
            try:
                base = str(suggested).strip().replace(' ', '_')
            except Exception:
                base = 'reporte'
        else:
            base = None
        return filedialog.asksaveasfilename(parent=parent, defaultextension='.pdf', initialfile=base, filetypes=[('PDF files', '*.pdf')])
    except Exception:
        return None


def _open_pdf_file(file_path: str, parent: Optional[object] = None) -> bool:
    try:
        if os.name == 'nt':
            os.startfile(file_path)
            return True
        return False
    except Exception:
        try:
            if parent is not None:
                messagebox.showwarning('Aviso', f'No se pudo abrir el PDF automáticamente. Archivo: {file_path}', parent=parent)
        except Exception:
            pass
        return False


def _ensure_reportlab(parent: Optional[object] = None) -> bool:
    try:
        import reportlab  # type: ignore
        return True
    except Exception:
        messagebox.showerror('Error', "No se encontró 'reportlab'. Instala reportlab (ej: pip install reportlab)", parent=parent)
        return False


def _ask_select_deposits(parent, db_path: str):
    """Show a modal dialog with deposit checkboxes and return selected deposit_ids or None.

    Returns a list of deposit_id (ints) if the user selected one or more deposits,
    or None if the user cancelled or selected none.
    """
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return None

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT deposit_id, deposit_description FROM deposits ORDER BY deposit_description")
        deps = cur.fetchall()
        conn.close()
    except Exception:
        return None

    if not deps:
        return None

    win = tk.Toplevel(parent)
    win.title('Seleccionar Depósitos')
    win.transient(parent)
    win.grab_set()

    lbl = ttk.Label(win, text='Seleccione depósitos (marca "Todos" o elija individualmente):')
    lbl.pack(padx=8, pady=(8, 4))

    # scrollable frame for many checkboxes
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

    # 'Todos' checkbox
    vars_list = []
    id_map = []
    todos_var = tk.IntVar(value=1)

    def _set_all(v=None):
        val = todos_var.get()
        for vv in vars_list:
            vv.set(bool(val))

    chk_all = ttk.Checkbutton(frame_inner, text='Todos', variable=todos_var, command=_set_all)
    chk_all.pack(anchor='w', pady=2)

    for d in deps:
        did = d[0]
        ddesc = d[1] or str(did)
        var = tk.IntVar(value=1)
        cb = ttk.Checkbutton(frame_inner, text=ddesc, variable=var, onvalue=1, offvalue=0)
        cb.pack(anchor='w', padx=6)
        vars_list.append(var)
        id_map.append(did)

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

    sel_ids = None
    frm = ttk.Frame(win)
    frm.pack(padx=8, pady=8)

    def _on_ok():
        selected = [id_map[i] for i, v in enumerate(vars_list) if v.get()]
        nonlocal sel_ids
        sel_ids = selected if selected else None
        win.destroy()

    def _on_cancel():
        nonlocal sel_ids
        sel_ids = None
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
    return sel_ids


def generate_pdf_report_diferencias_resumen(parent, db_path: str = DEFAULT_DB):
    """Generate the differences summary report.

    Prompts the user to select deposits (checkbox dialog). If deposits are selected
    the report aggregates from `inventory_count`, otherwise it uses
    `inventory_count_res`.
    """

    # Ask deposits first
    try:
        sel_deps = _ask_select_deposits(parent, db_path)
    except Exception:
        sel_deps = None

    # Ask for file path
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return

    if not os.path.exists(db_path):
        messagebox.showerror('Error', f'No se encontró la base de datos: {db_path}', parent=parent)
        return

    rows = []
    deposit_label = ''
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        if sel_deps:
            placeholders = ','.join('?' for _ in sel_deps)
            try:
                cur.execute(f"SELECT deposit_description FROM deposits WHERE deposit_id IN ({placeholders})", tuple(sel_deps))
                descs = [d[0] for d in cur.fetchall() if d and d[0]]
                deposit_label = ' (' + ', '.join(descs or [str(d) for d in sel_deps]) + ')'
            except Exception:
                deposit_label = ' (' + ', '.join(str(d) for d in sel_deps) + ')'

            sql = '''
                SELECT ic.code_item AS code_item,
                       MAX(COALESCE(i.description_item, '')) AS description_item,
                       COALESCE(SUM(ic.total),0) AS total,
                       COALESCE(s.sales_qty,0) AS sales_qty,
                       COALESCE(p.purchasing_qty,0) AS purchasing_qty,
                       (COALESCE(SUM(ic.total),0) + COALESCE(p.purchasing_qty,0) - COALESCE(s.sales_qty,0)) AS total_calc,
                       MAX(COALESCE(i.current_inventory,0)) AS current_inventory,
                       (MAX(COALESCE(i.current_inventory,0)) - (COALESCE(SUM(ic.total),0) + COALESCE(p.purchasing_qty,0) - COALESCE(s.sales_qty,0))) AS difference
                  FROM inventory_count ic
                  LEFT JOIN items i ON i.code_item = ic.code_item
                  LEFT JOIN (
                      SELECT code_item, SUM(sales_qty) AS sales_qty FROM sales GROUP BY code_item
                  ) s ON s.code_item = ic.code_item
                  LEFT JOIN (
                      SELECT code_item, SUM(purchasing_qty) AS purchasing_qty FROM purchasing GROUP BY code_item
                  ) p ON p.code_item = ic.code_item
                 WHERE ic.deposit_id IN (%s)
                 GROUP BY ic.code_item
            ''' % (placeholders)
            cur.execute(sql, tuple(sel_deps))
            rows = cur.fetchall()
        else:
            cur.execute('PRAGMA table_info(inventory_count_res)')
            cols = [c[1] for c in cur.fetchall()]
            sel_cols = ['code_item']
            sel_cols.append('description_item' if 'description_item' in cols else "'' AS description_item")
            sel_cols.append('total' if 'total' in cols else '0 AS total')
            sel_cols.append('sales_qty' if 'sales_qty' in cols else '0 AS sales_qty')
            sel_cols.append('purchasing_qty' if 'purchasing_qty' in cols else '0 AS purchasing_qty')
            sel_cols.append('total_calc' if 'total_calc' in cols else '0 AS total_calc')
            sel_cols.append('current_inventory' if 'current_inventory' in cols else '0 AS current_inventory')

            if 'difference' in cols:
                diff_expr = 'difference'
            elif 'total_calc' in cols and 'current_inventory' in cols:
                diff_expr = '(current_inventory - total_calc)'
            elif 'total' in cols and 'current_inventory' in cols:
                diff_expr = '(current_inventory - total)'
            else:
                diff_expr = '0'

            sql = f"SELECT {', '.join(sel_cols)}, {diff_expr} AS difference FROM inventory_count_res"
            cur.execute(sql)
            rows = cur.fetchall()

        conn.close()
    except Exception as e:
        messagebox.showerror('Error', f'Error al leer la base de datos: {e}', parent=parent)
        return

    # Ensure ordering by absolute difference desc
    try:
        rows = sorted(rows, key=lambda r: abs(r[-1]) if r and len(r) and isinstance(r[-1], (int, float)) else abs(float(r[-1])) if r and len(r) else 0, reverse=True)
    except Exception:
        try:
            rows = sorted(rows, key=lambda r: abs(float(r[-1])) if r and len(r) else 0, reverse=True)
        except Exception:
            pass

    # Build PDF
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal = styles['Normal']

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    if sel_deps:
        story.append(Paragraph(f'Reporte Diferencias - Resumen{deposit_label}', title_style))
    else:
        story.append(Paragraph('Reporte Diferencias - Resumen (inventory_count_res)', title_style))
    story.append(Spacer(1, 8))

    headers = ['Código', 'Descripción', 'Total', 'Sales', 'Purchasing', 'Total_calc', 'Actual', 'Diferencia']
    data = [headers]
    for r in rows:
        # normalize length
        vals = list(r)
        # pad to expected length
        while len(vals) < 8:
            vals.append('')
        data.append([
            vals[0] or '',
            (vals[1] or '')[:200],
            str(vals[2] or 0),
            str(vals[3] or 0),
            str(vals[4] or 0),
            str(vals[5] or 0),
            str(vals[6] or 0),
            str(abs(vals[7] or 0))
        ])

    if len(data) == 1:
        story.append(Paragraph('No hay registros para reportar.', normal))
    else:
        table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=[80, 360, 60, 60, 60, 60, 60, 60])
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror('Error', f'Error al generar el PDF: {e}', parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo('OK', f'Reporte PDF generado: {file_path}', parent=parent)


def add_pdf_report_diferencias_resumen_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = 'Diferencias Resumen'):
    try:
        from tkinter import ttk
        btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_diferencias_resumen(parent_frame, db_path))
        try:
            btn.grid(row=33, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_diferencias_resumen(parent_frame, db_path))
        try:
            btn.grid(row=33, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn


def _debug_button_registered():
    print('DEBUG: add_pdf_report_diferencias_resumen_button available in resumen module')


def generate_pdf_report_nocode_items(parent, db_path: str = DEFAULT_DB):
    """Genera un PDF con los registros de la tabla `nocode_items`.
    La función adapta las columnas disponibles y muestra una tabla simple.
    """
    # Ask deposits first so user always sees the selection dialog before the save dialog
    try:
        sel_deps = _ask_select_deposits(parent, db_path)
    except Exception:
        sel_deps = None

    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror('Error', f'No se encontró la base de datos: {db_path}', parent=parent)
        return

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # get columns
        cur.execute("PRAGMA table_info(nocode_items)")
        cols_info = cur.fetchall()
        if not cols_info:
            messagebox.showinfo('Info', 'La tabla `nocode_items` no existe o está vacía.', parent=parent)
            conn.close()
            return
        cols = [c[1] for c in cols_info]
        sql = f"SELECT {', '.join(cols)} FROM nocode_items ORDER BY rowid ASC"
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror('Error', f'Error al leer la base de datos: {e}', parent=parent)
        return

    # reportlab imports
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal = styles['Normal']

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph('Registros Sin codigo (nocode_items)', title_style))
    story.append(Spacer(1, 8))

    headers = [c.replace('_', ' ').title() for c in cols]
    data = [headers]
    for r in rows:
        row_vals = []
        for v in r:
            s = '' if v is None else str(v)
            # truncate long text
            if len(s) > 200:
                s = s[:197] + '...'
            row_vals.append(s)
        data.append(row_vals)

    if len(data) == 1:
        story.append(Paragraph('No hay registros para reportar.', normal))
    else:
        # compute approximate col widths
        total_width = 780
        col_width = max(40, int(total_width / max(1, len(headers))))
        col_widths = [col_width] * len(headers)
        table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=col_widths)
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror('Error', f'Error al generar el PDF: {e}', parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo('OK', f'Reporte PDF generado: {file_path}', parent=parent)


def add_pdf_report_nocode_items_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = 'Registros Sin codigo'):
    try:
        from tkinter import ttk
        btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_nocode_items(parent_frame, db_path))
        try:
            btn.grid(row=34, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_nocode_items(parent_frame, db_path))
        try:
            btn.grid(row=34, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn


def generate_pdf_report_items_not_in_inventory(parent, db_path: str = DEFAULT_DB):
    """Genera un PDF con los items de la tabla `items` que no tienen registros en `inventory_count`.
    Busca por `code_item` en ambas tablas.
    """
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror('Error', f'No se encontró la base de datos: {db_path}', parent=parent)
        return

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        sql = (
            "SELECT i.code_item, COALESCE(i.description_item, '') "
            "FROM items i "
            "WHERE NOT EXISTS (SELECT 1 FROM inventory_count ic WHERE ic.code_item = i.code_item) "
            "ORDER BY i.code_item ASC"
        )
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror('Error', f'Error al leer la base de datos: {e}', parent=parent)
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
    story.append(Paragraph('Items No en Inventario', title_style))
    story.append(Spacer(1, 8))

    headers = ['Código', 'Descripción']
    data = [headers]
    for r in rows:
        code = r[0] or ''
        desc = (r[1] or '')[:300]
        data.append([code, desc])

    if len(data) == 1:
        story.append(Paragraph('No hay registros para reportar.', normal))
    else:
        col_widths = [120, 600]
        table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=col_widths)
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror('Error', f'Error al generar el PDF: {e}', parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo('OK', f'Reporte PDF generado: {file_path}', parent=parent)


def add_pdf_report_items_not_in_inventory_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = 'Items no en Inventario'):
    try:
        from tkinter import ttk
        btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_items_not_in_inventory(parent_frame, db_path))
        try:
            btn.grid(row=35, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_items_not_in_inventory(parent_frame, db_path))
        try:
            btn.grid(row=35, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn


def generate_pdf_report_verificacion_remarks(parent, db_path: str = DEFAULT_DB):
    """Generate a verification-style report but only include records where remarks is not empty."""
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror('Error', f'No se encontró la base de datos: {db_path}', parent=parent)
        return

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
    WHERE ic.remarks IS NOT NULL AND TRIM(ic.remarks) <> ''
    ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.id ASC;
    """

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        messagebox.showerror('Error', f'Error al leer la base de datos: {e}', parent=parent)
        return

    grouped = {}
    for row in rows:
        counter_name, deposito, rack = row[0], row[1], row[2]
        grouped.setdefault(counter_name, {}).setdefault(deposito, {}).setdefault(rack, []).append(row)

    # lazy imports for reportlab
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    contador_style = styles['Heading2']
    deposito_style = styles['Heading3']
    rack_style = styles['Heading4']
    normal = styles['Normal']

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    story = []
    story.append(Paragraph('Reporte Verificación (con Remarks)', title_style))
    story.append(Spacer(1, 8))

    col_headers = ['Ubicación', 'Código', 'Producto', 'Cajas', 'U/caja', 'Tot. U/cajas', 'Sueltos', 'Total', 'ID', 'Comentarios']
    for ci, (counter_name, depositos) in enumerate(grouped.items()):
        story.append(Paragraph(f'Contador: {counter_name}', contador_style))
        story.append(Spacer(1, 6))
        for deposito, racks in depositos.items():
            story.append(Paragraph(f'Depósito: {deposito}', deposito_style))
            story.append(Spacer(1, 4))
            for rack, items in racks.items():
                story.append(Paragraph(f'Rack: {rack} — {len(items)} registros', rack_style))
                story.append(Spacer(1, 4))
                data = [col_headers]
                for r in items:
                    data.append([
                        r[3] or '',
                        r[4] or '',
                        (r[5] or '')[:60],
                        str(r[6] or 0),
                        str(r[7] or 0),
                        str(r[8] or 0),
                        str(r[9] or 0),
                        str(r[10] or 0),
                        str(r[11] or ''),
                        (r[12] or '')[:120]
                    ])
                table = Table(data, repeatRows=1, hAlign='LEFT', colWidths=[90, 60, 140, 35, 40, 45, 45, 45, 30, 120])
                tbl_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ])
                table.setStyle(tbl_style)
                story.append(table)
                story.append(Spacer(1, 8))
        if ci < len(grouped) - 1:
            story.append(PageBreak())

    if not grouped:
        story.append(Paragraph('No hay registros para reportar.', normal))

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror('Error', f'Error al generar el PDF: {e}', parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo('OK', f'Reporte PDF generado: {file_path}', parent=parent)


def add_pdf_report_verificacion_remarks_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = 'Verificación (Remarks)'):
    try:
        from tkinter import ttk
        btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_verificacion_remarks(parent_frame, db_path))
        try:
            btn.grid(row=27, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_verificacion_remarks(parent_frame, db_path))
        try:
            btn.grid(row=27, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    for r in rows:
        data.append([
            r[0] or '',
            (r[1] or '')[:200],
            str(r[2] or 0),
            str(r[3] or 0),
            str(r[4] or 0),
            str(r[5] or 0),
            str(abs(r[6] or 0))
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
        table.setStyle(tbl_style)
        story.append(table)

    try:
        doc.build(story)
    except Exception as e:
        messagebox.showerror('Error', f'Error al generar el PDF: {e}', parent=parent)
        return

    _open_pdf_file(file_path, parent=parent)
    messagebox.showinfo('OK', f'Reporte PDF generado: {file_path}', parent=parent)


def add_pdf_report_diferencias_resumen_button(parent_frame, db_path: str = DEFAULT_DB, button_text: str = 'Diferencias Resumen'):
    try:
        from tkinter import ttk
        btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_diferencias_resumen(parent_frame, db_path))
        try:
            btn.grid(row=33, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_diferencias_resumen(parent_frame, db_path))
        try:
            btn.grid(row=33, column=0, pady=8)
        except Exception:
            btn.pack(pady=8)
        return btn
