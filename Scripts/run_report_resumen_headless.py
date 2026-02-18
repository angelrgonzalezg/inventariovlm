import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import traceback

# Prefer the new resumen module; fall back to the original ui_pdf_report
try:
    import ui_pdf_report_resumen as rpt
except Exception:
    import ui_pdf_report as rpt

out = Path(repo_root) / 'tmp'
out.mkdir(exist_ok=True)
outfile = out / 'diferencias_resumen.pdf'

# Monkeypatch asksave and _open_pdf_file to avoid dialogs and opening
setattr(rpt, '_asksave', lambda parent: str(outfile))
setattr(rpt, '_open_pdf_file', lambda path, parent=None: True)

print('Calling generate_pdf_report_diferencias_resumen ->', outfile)
try:
    rpt.generate_pdf_report_diferencias_resumen(None, db_path=str(repo_root / 'inventariovlm.db'))
    print('Report completed, file exists:', outfile.exists(), 'size=', outfile.stat().st_size if outfile.exists() else 'n/a')
except Exception:
    print('Exception during report:')
    traceback.print_exc()
    raise
