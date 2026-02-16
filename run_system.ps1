# Trading AI - Unified Launcher

Write-Host 'Starting Backend...' -ForegroundColor Green
Start-Process -FilePath 'python' -ArgumentList '-m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0' -WorkingDirectory 'backend/src' -NoNewWindow

Write-Host 'Starting Frontend...' -ForegroundColor Cyan
Set-Location frontend
npm run dev