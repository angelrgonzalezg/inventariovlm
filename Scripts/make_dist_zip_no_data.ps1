Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipPath = Join-Path (Get-Location) 'dist\InventarioVLM_bundle_no_data.zip'
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
$zip = [System.IO.Compression.ZipFile]::Open($zipPath,'Create')
function Add-Entry($file, $entry) {
    try {
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file, $entry, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    } catch {
        Write-Host ("Skipping " + $file + ": " + $_.Exception.Message)
    }
}
# Add exe
$exe = Join-Path (Get-Location) 'dist\InventarioVLM.exe'
if (Test-Path $exe) { Add-Entry $exe 'InventarioVLM.exe' } else { Write-Host "Executable not found: $exe" }
# Add folders except csv
$folders = @('icons','pdf')
foreach ($f in $folders) {
    $src = Join-Path (Get-Location) $f
    if (Test-Path $src) {
        Get-ChildItem -Path $src -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($src.Length + 1) -replace '\\','/'
            $entry = "$f/" + $rel
            Add-Entry $_.FullName $entry
        }
    }
}
$zip.Dispose()
Write-Host "Created bundle: $zipPath"
