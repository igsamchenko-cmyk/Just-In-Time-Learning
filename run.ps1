$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".runtime\python\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Локальний Python не знайдено. Очікуваний шлях: $python"
}

& $python -m uvicorn app.main:app --reload
