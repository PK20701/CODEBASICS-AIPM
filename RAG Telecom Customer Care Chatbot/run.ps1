# Launch the NovaCell care assistant UI.
#   Right-click > Run with PowerShell, or:  .\run.ps1
# Works from any directory -- paths are resolved relative to this script.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "No virtual environment found at .venv. Create it with: uv venv .venv --python 3.13"
}

# Build the knowledge base on first run (the app needs a populated store).
if (-not (Test-Path (Join-Path $root "chroma_store"))) {
    Write-Host "No chroma_store found - building the knowledge base first..."
    & $python (Join-Path $root "ingest_all.py")
}

& $python -m streamlit run (Join-Path $root "app.py")
