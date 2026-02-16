param(
    [string]$DistDir = "dist",
    [string]$ExeName = "InventarioVLM.exe",
    [string[]]$Folders = @("icons", "pdf", "csv")
)

$ErrorActionPreference = 'Continue'
$zipPath = Join-Path -Path (Get-Location) -ChildPath (Join-Path $DistDir "InventarioVLM_bundle.zip")
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, 'Create')

function Add-FileToZip([string]$filePath, [string]$entryName) {
    try {
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $filePath, $entryName, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    } catch {
        Write-Host "Skipping locked/unreadable file: $filePath -- $($_.Exception.Message)"
    }
}

# Add exe
$exePath = Join-Path (Get-Location) (Join-Path $DistDir $ExeName)
if (Test-Path $exePath) {
    Add-FileToZip $exePath $ExeName
} else {
    Write-Host "Executable not found: $exePath"
}

# Add folders
foreach ($f in $Folders) {
    $src = Join-Path (Get-Location) $f
    if (Test-Path $src) {
        Get-ChildItem -Path $src -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($src.Length + 1) -replace '\\', '/'
            $entry = "$f/" + $rel
            Add-FileToZip $_.FullName $entry
        }
    }
}

$zip.Dispose()
Write-Host "Created bundle:" $zipPath
