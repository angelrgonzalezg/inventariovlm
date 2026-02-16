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
    return filedialog.asksaveasfilename(parent=parent, defaultextension=".pdf",
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
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
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


def generate_pdf_report_por_deposito(parent, db_path: str = DEFAULT_DB):
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
        return

    sql = """
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
        ic.total AS total
    FROM inventory_count ic
    LEFT JOIN deposits d ON ic.deposit_id = d.deposit_id
    LEFT JOIN racks r ON ic.rack_id = r.rack_id
    LEFT JOIN items i on ic.code_item = i.code_item
    ORDER BY d.deposit_description ASC, r.rack_description ASC, ic.code_item ASC;
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
    file_path = _asksave(parent)
    if not file_path:
        return
    if not _ensure_reportlab(parent):
        return
    if not os.path.exists(db_path):
        messagebox.showerror("Error", f"No se encontró la base de datos: {db_path}", parent=parent)
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
    ORDER BY ic.counter_name ASC, d.deposit_description ASC, r.rack_description ASC, ic.id ASC;
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
            str(r[3] or 0),
            str(r[4] or 0),
            str(r[5] or 0),
            str(r[6] or 0),
            str(r[7] or 0),
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