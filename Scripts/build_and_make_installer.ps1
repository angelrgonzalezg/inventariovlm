# Wrapper script: builds exe with build_windows_exe.ps1 then builds Inno Setup installer if available
# Usage: .\scripts\build_and_make_installer.ps1 [-Debug]
param(
    [switch]$Debug,
    [string]$venvDir = ".venv",
    [string]$entryScript = "app.py",
    [string]$exeName = "InventarioVLM",
    [string]$distDir = "dist"
)

$ErrorActionPreference = 'Stop'

$buildScript = Join-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) -ChildPath 'build_windows_exe.ps1'
if (-not (Test-Path $buildScript)) {
    Write-Error "Build script not found: $buildScript"
    exit 1
}

# Run the build script
Write-Host "Running build script..."
$debugFlag = $null
if ($Debug) { $debugFlag = '-DebugBuild' }
& $buildScript -venvDir $venvDir -entryScript $entryScript -exeName $exeName -distDir $distDir $debugFlag

# After build, try to create installer with Inno Setup (ISCC.exe)
$iss = Join-Path -Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) -ChildPath '..\installer\InventarioVLM_installer.iss'
$iss = (Resolve-Path $iss).ProviderPath

if (Get-Command -Name ISCC.exe -ErrorAction SilentlyContinue) {
    Write-Host "ISCC.exe found. Building installer..."
    & ISCC.exe $iss
    Write-Host "Installer build completed. Check output folder for InventarioVLM_Installer.exe"
} else {
    Write-Warning "ISCC.exe not found in PATH. Skipping installer creation. Install Inno Setup or add ISCC.exe to PATH to enable this step."
}

Write-Host "All done."
