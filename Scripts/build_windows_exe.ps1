# Build script for Windows: creates venv, installs deps and builds exe with PyInstaller
# Usage (from project root PowerShell):
#   .\scripts\build_windows_exe.ps1

param(
    [string]$venvDir = ".venv",
    [string]$entryScript = "app.py",
    [string]$exeName = "InventarioVLM",
    [string]$distDir = "dist",
    [string]$specExtra = "",
    [switch]$DebugBuild
)

$ErrorActionPreference = 'Stop'

Write-Host "Starting Windows build script for InventarioVLM"

# 1) Create or reuse virtualenv
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment in $venvDir..."
    python -m venv $venvDir
} else {
    Write-Host "Using existing virtual environment: $venvDir"
}

$pip = "$venvDir\Scripts\pip.exe"
$python = "$venvDir\Scripts\python.exe"

Write-Host "Upgrading pip..."
& $pip install --upgrade pip

# 2) Install requirements + pyinstaller
if (Test-Path "requirements.txt") {
    Write-Host "Installing requirements.txt..."
    & $pip install -r requirements.txt
}
Write-Host "Installing/ensuring pyinstaller is available..."
& $pip install pyinstaller

# 3) Build with PyInstaller
# If your app includes folders like `icons`, `pdf`, `csv` or others, add them with --add-data
$addData = @()
# Add example resource folders if present
if (Test-Path "icons") { $addData += '"icons;icons"' }
if (Test-Path "pdf")   { $addData += '"pdf;pdf"' }
if (Test-Path "csv")   { $addData += '"csv;csv"' }

$addDataArgs = ""
if ($addData.Count -gt 0) { $addDataArgs = $addData -join ' ' }

if ($DebugBuild) {
     Write-Host "Debug build requested: producing a folder build with console (easier for debugging)."
     $pyinstallerArgs = @()
     $pyinstallerArgs += "--noconfirm"
     $pyinstallerArgs += "--clean"
     # folder build makes debugging and resource inspection easier
     $pyinstallerArgs += "--name $exeName"
     # leave console enabled
     if ($addDataArgs) { $pyinstallerArgs += $addDataArgs }
     if ($specExtra) { $pyinstallerArgs += $specExtra }
     $pyinstallerArgs += $entryScript
     $pyinstallerArgs = $pyinstallerArgs -join ' '
} else {
     $pyinstallerArgs = "--noconfirm --clean --onefile --noconsole --name $exeName $addDataArgs $specExtra $entryScript"
}
Write-Host "Running PyInstaller: $pyinstallerArgs"
& $python -m pyinstaller $pyinstallerArgs

Write-Host "Build completed. Check the $distDir\$exeName.exe"
Write-Host "To build an installer, see the installer template: installer\InventarioVLM_installer.iss"

Write-Host "Done."