<#
Simple uninstaller for InventarioVLM created by install.ps1
Run as Administrator to remove Program Files installation and shortcuts.
#>
param(
    [string]$InstallDir = "$env:ProgramFiles\\InventarioVLM",
    [switch]$RemoveDesktopShortcut = $true,
    [switch]$RemoveStartMenuShortcut = $true
)

function Test-IsAdmin {
    $currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Warning "Ejecute este script como Administrador para desinstalar correctamente."
    Pause
    exit 1
}

if (Test-Path -Path $InstallDir) {
    Write-Host "Eliminando carpeta: $InstallDir"
    Remove-Item -Path $InstallDir -Recurse -Force
} else {
    Write-Host "No existe la carpeta de instalación: $InstallDir"
}

$wsh = New-Object -ComObject WScript.Shell
$lnkName = 'Inventario VLM.lnk'
if ($RemoveStartMenuShortcut) {
    $startMenu = [Environment]::GetFolderPath('Programs')
    $lnkPath = Join-Path $startMenu $lnkName
    if (Test-Path -Path $lnkPath) { Remove-Item -Path $lnkPath -Force }
}
if ($RemoveDesktopShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnkPath = Join-Path $desktop $lnkName
    if (Test-Path -Path $lnkPath) { Remove-Item -Path $lnkPath -Force }
}
Write-Host "Desinstalación completada."