$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".runtime\python\python.exe"
$alembic = Join-Path $PSScriptRoot ".runtime\python\Scripts\alembic.exe"

if (-not (Test-Path $python)) {
    Write-Error "Локальний Python не знайдено. Очікуваний шлях: $python"
}

if (-not (Test-Path $alembic)) {
    & $python -m pip install -r requirements.txt
}

& $alembic upgrade head
