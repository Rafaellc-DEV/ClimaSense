# ClimaSense — sobe a API (porta 8000) e o frontend (porta 5173) para desenvolvimento no Windows.
# Primeira vez:
#   py -3.12 -m venv .venv ; .\.venv\Scripts\pip install -e ".\backend[dev]"
#   cd frontend ; npm install ; cd ..
#   Copy-Item .env.example .env   (e preencha)
$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Ambiente Python não encontrado. Rode: py -3.12 -m venv .venv" }

$api = Start-Process -PassThru -NoNewWindow -FilePath $python `
  -ArgumentList "-m", "uvicorn", "climasense.api.main:app", "--reload", "--port", "8000", "--app-dir", "backend" `
  -WorkingDirectory $raiz
try {
  Push-Location (Join-Path $raiz "frontend")
  npm run dev
} finally {
  Pop-Location
  Stop-Process -Id $api.Id -ErrorAction SilentlyContinue
}
