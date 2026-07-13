# Create a Desktop shortcut for the Lumen Gallery app.
# Windowless launch via the venv pythonw.exe, custom icon, OneDrive-aware Desktop.
$ErrorActionPreference = "Stop"

$here    = $PSScriptRoot
$repo    = Split-Path -Parent (Split-Path -Parent $here)   # app\gallery -> app -> repo
$pythonw = Join-Path $repo ".venv\Scripts\pythonw.exe"
$script  = Join-Path $here "lumen_gallery.pyw"
$icon    = Join-Path $here "icon.ico"

foreach ($p in @($pythonw, $script, $icon)) {
    if (-not (Test-Path $p)) { throw "missing: $p" }
}

$desktop = [Environment]::GetFolderPath("Desktop")   # respects OneDrive redirection
$lnk     = Join-Path $desktop "Lumen Gallery.lnk"

$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut($lnk)
$s.TargetPath       = $pythonw
$s.Arguments        = '"' + $script + '"'
$s.WorkingDirectory = $repo
$s.IconLocation     = $icon
$s.Description       = "Browse Lumen art and send it to the LED wall"
$s.WindowStyle      = 1
$s.Save()

Write-Output "Shortcut created: $lnk"
Write-Output "  target : $pythonw"
Write-Output "  script : $script"
Write-Output "  icon   : $icon"
