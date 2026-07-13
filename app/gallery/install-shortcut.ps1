# Create a Desktop shortcut for the built Lumen Gallery app.
# Points at the PyInstaller exe (run build.ps1 first), OneDrive-aware Desktop.
# If the exe isn't built yet, falls back to the windowless pythonw launch.
$ErrorActionPreference = "Stop"

$here = $PSScriptRoot
$repo = Split-Path -Parent (Split-Path -Parent $here)   # app\gallery -> app -> repo
$exe  = Join-Path $here "dist\Lumen Gallery.exe"
$icon = Join-Path $here "icon.ico"

if (Test-Path $exe) {
    $target = $exe; $args = ""
} else {
    Write-Output "exe not found (run build.ps1) — using pythonw fallback"
    $target = Join-Path $repo ".venv\Scripts\pythonw.exe"
    $args   = '"' + (Join-Path $here "lumen_gallery.pyw") + '"'
}

$desktop = [Environment]::GetFolderPath("Desktop")   # respects OneDrive redirection
$lnk     = Join-Path $desktop "Lumen Gallery.lnk"

$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut($lnk)
$s.TargetPath       = $target
$s.Arguments        = $args
$s.WorkingDirectory = $here
$s.IconLocation     = $icon
$s.Description       = "Browse Lumen art, launch shows, and drive the LED wall"
$s.WindowStyle      = 1
$s.Save()

Write-Output "Shortcut created: $lnk"
Write-Output "  target : $target"
