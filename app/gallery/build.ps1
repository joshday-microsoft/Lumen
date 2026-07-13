# Build the Lumen Gallery into a standalone Windows .exe (PyInstaller, one file).
# Output: app\gallery\dist\Lumen Gallery.exe  (icon embedded)
$ErrorActionPreference = "Stop"

$here = $PSScriptRoot
$repo = Split-Path -Parent (Split-Path -Parent $here)
$py   = Join-Path $repo ".venv\Scripts\python.exe"
$icon = Join-Path $here "icon.ico"
$src  = Join-Path $here "lumen_gallery.pyw"

Write-Output "Ensuring PyInstaller is installed..."
& $py -m pip install --quiet --disable-pip-version-check pyinstaller

Write-Output "Building Lumen Gallery.exe..."
& $py -m PyInstaller --noconfirm --onefile --windowed `
    --name "Lumen Gallery" `
    --icon $icon `
    --add-data "$icon;." `
    --distpath (Join-Path $here "dist") `
    --workpath (Join-Path $here "build") `
    --specpath $here `
    $src

$exe = Join-Path $here "dist\Lumen Gallery.exe"
if (Test-Path $exe) {
    Write-Output "OK -> $exe"
} else {
    throw "build failed: $exe not found"
}
