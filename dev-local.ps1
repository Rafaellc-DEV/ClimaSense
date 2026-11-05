# ClimaSense — desenvolvimento 100% local: Postgres e Mongo em Docker, sem tocar no Neon nem no Atlas do .env.
# Primeira vez: cria os contêineres, aplica as migrações e carrega o território.
#   powershell -ExecutionPolicy Bypass -File .\dev-local.ps1 -Preparar
# Depois, só subir:
#   powershell -ExecutionPolicy Bypass -File .\dev-local.ps1
param([switch]$Preparar)
$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"

# As variáveis de ambiente têm prioridade sobre o .env (pydantic-settings).
$env:DATABASE_URL = "postgresql+psycopg2://climasense:climasense@localhost:55433/climasense"
$env:MONGO_URI = "mongodb://localhost:27018/"

function Garantir-Conteiner($nome, $argumentos) {
  if (-not (docker ps -a --format "{{.Names}}" | Select-String -SimpleMatch -Quiet $nome)) {
    docker run -d --name $nome @argumentos | Out-Null
  } else {
    docker start $nome | Out-Null
  }
}
Garantir-Conteiner "climasense-pg-dev" @("-e", "POSTGRES_USER=climasense", "-e", "POSTGRES_PASSWORD=climasense",
  "-e", "POSTGRES_DB=climasense", "-p", "55433:5432", "-v", "climasense-pg-dev:/var/lib/postgresql/data", "postgres:16-alpine")
Garantir-Conteiner "climasense-mongo-dev" @("-p", "27018:27017", "-v", "climasense-mongo-dev:/data/db", "mongo:7")

if ($Preparar) {
  Start-Sleep -Seconds 5
  Push-Location (Join-Path $raiz "backend")
  try {
    & (Join-Path $raiz ".venv\Scripts\alembic.exe") upgrade head
    & $python -m climasense.territorio carregar
    & $python -m climasense.etl atualizar
  } finally { Pop-Location }
}

& (Join-Path $raiz "dev.ps1")
