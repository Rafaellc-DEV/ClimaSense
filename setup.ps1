# ClimaSense — prepara o ambiente no Windows (rode uma vez no terminal do VS Code, na pasta ClimaSense):
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# Cria a .venv nesta pasta, instala todas as bibliotecas Python e do frontend e prepara o .env.
$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz

function Achar-Python {
  foreach ($v in @("3.13", "3.12")) {
    try { & py "-$v" -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { return @("py", "-$v") } } catch {}
  }
  try {
    $ver = & python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
    if ([version]$ver -ge [version]"3.12") { return @("python") }
  } catch {}
  throw "Python 3.12 ou mais novo não encontrado. Instale em https://www.python.org/downloads/ e marque 'Add to PATH'."
}

Write-Host "1/5 Criando o ambiente virtual .venv..." -ForegroundColor Cyan
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  $py = Achar-Python
  & $py[0] $py[1..($py.Length - 1)] -m venv .venv
}
$python = Join-Path $raiz ".venv\Scripts\python.exe"

Write-Host "2/5 Instalando as bibliotecas Python (backend + ETL + testes)..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip
& $python -m pip install -r backend\requirements-dev.txt
& $python -m pip install -e backend --no-deps

Write-Host "3/5 Instalando as bibliotecas do frontend (npm)..." -ForegroundColor Cyan
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Warning "Node.js não encontrado. Instale o Node 22 em https://nodejs.org e rode este script de novo."
} else {
  Push-Location frontend; npm ci; Pop-Location
}

Write-Host "4/5 Preparando o arquivo .env..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
  Copy-Item .env.example .env
  $segredo = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
  (Get-Content .env) -replace '^SESSION_SECRET=$', "SESSION_SECRET=$segredo" | Set-Content .env -Encoding utf8
  Write-Host "   .env criado. Preencha MONGO_URI e DATABASE_URL (as mesmas do ETL anterior)." -ForegroundColor Yellow
} else {
  Write-Host "   .env já existe; nada foi alterado."
}

Write-Host "5/5 Ativando a proteção contra vazamento de senhas no git (pre-commit)..." -ForegroundColor Cyan
& (Join-Path $raiz ".venv\Scripts\pre-commit.exe") install

Write-Host ""
Write-Host "Pronto. No VS Code, escolha o interpretador .venv\Scripts\python.exe (Ctrl+Shift+P > Python: Select Interpreter)." -ForegroundColor Green
Write-Host "Testes: cd backend; ..\.venv\Scripts\pytest     |     cd frontend; npm test"
