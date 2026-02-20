<#
Simple installer PowerShell script for InventarioVLM
Usage: Run this script from the installer folder (where `InventarioVLM.exe` and `inventariovlm.db` live).
It will copy files to the chosen installation folder (defaults to Program Files), and create Start Menu and Desktop shortcuts.
#>
param(
    [string]$InstallDir = "$env:ProgramFiles\\InventarioVLM",
    [switch]$CreateDesktopShortcut = $true,
    [switch]$CreateStartMenuShortcut = $true
)

Write-Host "Instalador de InventarioVLM"
Write-Host "Instalando en: $InstallDir"

if (-not (Test-Path -Path $PSScriptRoot)) {
    $PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
}

# Ensure running as admin for ProgramFiles write access
function Test-IsAdmin {
    $currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Warning "Se recomienda ejecutar este instalador como Administrador para instalar en Program Files. Se aborta si no es admin."
    Pause
    exit 1
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Copy all files from installer folder to target
Write-Host "Copiando archivos..."
Get-ChildItem -Path $PSScriptRoot -File | ForEach-Object {
    $src = $_.FullName
    $dest = Join-Path $InstallDir $_.Name
    Copy-Item -Path $src -Destination $dest -Force
}

# Copy icons folder if present
if (Test-Path -Path (Join-Path $PSScriptRoot 'icons')) {
    $destIcons = Join-Path $InstallDir 'icons'
    New-Item -ItemType Directory -Path $destIcons -Force | Out-Null
    Copy-Item -Path (Join-Path $PSScriptRoot 'icons\*') -Destination $destIcons -Recurse -Force
}

# Create shortcuts
$wsh = New-Object -ComObject WScript.Shell
$exePath = Join-Path $InstallDir 'InventarioVLM.exe'
$lnkName = 'Inventario VLM.lnk'

if ($CreateStartMenuShortcut) {
    $startMenu = [Environment]::GetFolderPath('Programs')
    $lnkPath = Join-Path $startMenu $lnkName
    $shortcut = $wsh.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = (Join-Path $InstallDir 'icons\\cj_electrical_supplies.ico')
    $shortcut.Save()
    Write-Host "Acceso directo creado en el menú Inicio: $lnkPath"
}

if ($CreateDesktopShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnkPath = Join-Path $desktop $lnkName
    $shortcut = $wsh.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = (Join-Path $InstallDir 'icons\\cj_electrical_supplies.ico')
    $shortcut.Save()
    Write-Host "Acceso directo creado en el Escritorio: $lnkPath"
}

Write-Host "Instalación completada en: $InstallDir"
Write-Host "Para desinstalar ejecute 'uninstall.ps1' desde la misma carpeta y/o elimine los accesos directos."