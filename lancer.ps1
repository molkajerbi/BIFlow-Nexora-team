# Lance BIFlow : l'API (FastAPI, port 8000) et l'application web (Next.js, port 3000), chacune dans sa fenêtre.
# Utilisation, depuis la racine du projet :   .\lancer.ps1
$racine = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$racine'; .\.venv\Scripts\Activate.ps1; uvicorn api.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$racine\web'; npm run dev"
Start-Sleep -Seconds 8
Start-Process "http://localhost:3000"
