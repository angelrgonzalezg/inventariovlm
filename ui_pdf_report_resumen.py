import os
import sqlite3
from typing import Optional
from tkinter import filedialog, messagebox

DEFAULT_DB = "inventariovlm.db"


def _asksave(parent: Optional[object]) -> Optional[str]:
    try:
        return filedialog.asksaveasfilename(parent=parent, defaultextension='.pdf', filetypes=[('PDF files', '*.pdf')])
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


def generate_pdf_report_diferencias_resumen(parent, db_path: str = DEFAULT_DB):
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
        cur.execute('PRAGMA table_info(inventory_count_res)')
        cols = [c[1] for c in cur.fetchall()]

        sel_cols = ['code_item']
        sel_cols.append('description_item' if 'description_item' in cols else "'' AS description_item")
        sel_cols.append('total' if 'total' in cols else '0 AS total')
        sel_cols.append('sales_qty' if 'sales_qty' in cols else '0 AS sales_qty')
        sel_cols.append('purchasing_qty' if 'purchasing_qty' in cols else '0 AS purchasing_qty')
        sel_cols.append('total_calc' if 'total_calc' in cols else '0 AS total_calc')
        # include current_inventory as 'Actual' column if present
        sel_cols.append('current_inventory' if 'current_inventory' in cols else '0 AS current_inventory')

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
        messagebox.showerror('Error', f'Error al leer la base de datos: {e}', parent=parent)
        return

    # lazy imports for reportlab
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

    headers = ['Código', 'Descripción', 'Total', 'Sales', 'Purchasing', 'Total_calc', 'Actual', 'Diferencia']
    data = [headers]
    for r in rows:
        data.append([
            r[0] or '',
            (r[1] or '')[:200],
            str(r[2] or 0),
            str(r[3] or 0),
            str(r[4] or 0),
            str(r[5] or 0),
            str(r[6] or 0),
            str(abs(r[7] or 0))
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


def generate_pdf_report_nocode_items(parent, db_path: str = DEFAULT_DB):
    """Genera un PDF con los registros de la tabla `nocode_items`.
    La función adapta las columnas disponibles y muestra una tabla simple.
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
