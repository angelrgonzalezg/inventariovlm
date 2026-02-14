# Build Windows executable and installer (InventarioVLM)

This document shows steps to produce a portable Windows executable and an installer (.exe) using PyInstaller and Inno Setup.

Prerequisites on your Windows machine:
- Python 3.10+ installed and on PATH
- Git (optional)
- Inno Setup (for the installer): https://jrsoftware.org/isinfo.php (make sure `ISCC.exe` is in your PATH)

Quick automated build (PowerShell):

1. From project root open PowerShell and run:

```powershell
# make script executable if required
.
# run the build script
.\scripts\build_windows_exe.ps1
```

The script will create (or reuse) `.venv`, install requirements from `requirements.txt`, install `pyinstaller` and run PyInstaller. The final exe will be in `dist\InventarioVLM.exe`.

Custom PyInstaller options:
- The script uses `--onefile` and `--noconsole` (GUI app). If you want a console for debugging remove `--noconsole`.
- If you have extra resource folders (icons, pdf, csv) the script will add them automatically if present; edit the script to include other files.

Build installer with Inno Setup:

1. Ensure `ISCC.exe` is in your PATH (Inno Setup installation does this if you check the option). If not, open Inno Setup and compile the `installer\InventarioVLM_installer.iss` template.

2. From command line:

```powershell
ISCC.exe installer\InventarioVLM_installer.iss
```

The output installer will be `InventarioVLM_Installer.exe` in the current directory.

Notes & troubleshooting:
- If PyInstaller misses data files (icons, pdf templates, etc.) add explicit `--add-data` entries in `scripts\build_windows_exe.ps1` (Windows syntax: `"source;dest"`).
- Antivirus/SmartScreen may flag a newly built exe; code-signing solves that (not covered here).
- If the app requires other runtime files, include them under `[Files]` in the Inno Setup script.

If you want, I can:
- Add a `--debug` switch to the build script (generate non-onefile build for easier debugging).
- Try to produce a portable installer on your machine (I cannot run builds from here).