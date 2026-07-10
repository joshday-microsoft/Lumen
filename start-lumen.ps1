# Start the Lumen daemon (LED wall bridge) on port 7788.
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
& $py -m uvicorn server.main:app --host 127.0.0.1 --port 7788 --app-dir $root
