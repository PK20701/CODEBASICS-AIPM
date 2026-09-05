# Launch the CLI REPL.  Type 'quit' to exit.
$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python (Join-Path $PSScriptRoot "main.py")
