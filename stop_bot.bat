@echo off
echo Stopping School Journal Bot...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$projectRoot = 'd:\school_journal_bot\venv\Scripts\'; Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { Stop-Process -Id $_.Id -Force }"
echo Bot stopped.
pause
