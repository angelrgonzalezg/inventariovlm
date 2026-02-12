DEFAULT_DB = "inventariovlm.db"

def add_pdf_report_por_contador_button(parent_frame, db_path=DEFAULT_DB, button_text="Reporte por Contador"):
    """
    Agrega un botón que genera un PDF agrupado por counter_name, luego por depósito y rack, con salto de página por contador.
    """
    try:
        from tkinter import ttk
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_por_contador(parent_frame, db_path))
        btn.grid(row=25, column=0, pady=8)
        return btn

    btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_por_contador(parent_frame, db_path))
    try:
        btn.grid(row=25, column=0, pady=8)
    except Exception:
        btn.pack(pady=8)
    return btn

def generate_pdf_report_por_contador(parent, db_path=DEFAULT_DB):
    """
    Genera un PDF agrupado por counter_name, luego por depósito y rack, con salto de página por contador.
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
        i.description_item AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total
    FROM inventory_count ic
    INNER JOIN deposits d ON ic.deposit_id = d.deposit_id
    INNER JOIN racks r ON ic.rack_id = r.rack_id
    INNER JOIN items i on ic.code_item = i.code_item
    ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;
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
    story.append(Paragraph("Reporte por Contador", title_style))
    story.append(Spacer(1, 8))
    col_headers = ["Ubicación", "Código", "Producto", "Cajas", "U/caja", "Tot. U/cajas", "Sueltos", "Total"]
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
    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}")
DEFAULT_DB = "inventariovlm.db"

def add_pdf_report_por_deposito_button(parent_frame, db_path=DEFAULT_DB, button_text="Reporte por Depósito"):
    """
    Agrega un botón que genera un PDF agrupado por depósito, con salto de página por depósito y ruptura por rack.
    """
    try:
        from tkinter import ttk
    except Exception:
        from tkinter import Button as _Btn
        btn = _Btn(parent_frame, text=button_text, command=lambda: generate_pdf_report_por_deposito(parent_frame, db_path))
        btn.grid(row=24, column=0, pady=8)
        return btn

    btn = ttk.Button(parent_frame, text=button_text, command=lambda: generate_pdf_report_por_deposito(parent_frame, db_path))
    try:
        btn.grid(row=24, column=0, pady=8)
    except Exception:
        btn.pack(pady=8)
    return btn

def generate_pdf_report_por_deposito(parent, db_path=DEFAULT_DB):
    """
    Genera un PDF agrupado por depósito, con salto de página por depósito y ruptura por rack, usando el query proporcionado.
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
        d.deposit_description AS deposito,
        r.rack_description AS rack,
        ic.location AS ubicacion,
        ic.code_item AS producto_codigo,
        i.description_item AS producto,
        ic.boxqty AS cajas,
        ic.boxunitqty AS uni_x_cajas,
        ic.boxunittotal AS tot_uni_cajas,
        ic.magazijn AS sueltos,
        ic.total AS total
    FROM inventory_count ic
    INNER JOIN deposits d ON ic.deposit_id = d.deposit_id
    INNER JOIN racks r ON ic.rack_id = r.rack_id
    INNER JOIN items i on ic.code_item = i.code_item
    ORDER BY d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;
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
    # Agrupar por depósito y rack
    grouped = {}
    for row in rows:
        deposito, rack = row[0], row[1]
        if deposito not in grouped:
            grouped[deposito] = {}
        if rack not in grouped[deposito]:
            grouped[deposito][rack] = []
        grouped[deposito][rack].append(row)
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
        messagebox.showerror("Error", f"Error al generar el PDF: {e}")
        return
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
from tkinter import filedialog, messagebox
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

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
                    str(r[4] or 0),
                    str(r[5] or 0),
                    str(r[6] or 0),
                    str(r[7] or 0),
                    str(r[8] or 0),
                    str(r[9] or 0),
                    str(r[10] or 0),
                    str(r[11] or 0),
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

    messagebox.showinfo("OK", f"Reporte PDF generado: {file_path}")