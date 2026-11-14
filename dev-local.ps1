# ClimaSense — desenvolvimento 100% local: Postgres e Mongo em Docker, sem tocar no Neon nem no Atlas do .env.
# Primeira vez: cria os contêineres, aplica as migrações e carrega o território.
#   powershell -ExecutionPolicy Bypass -File .\dev-local.ps1 -Preparar
# Depois, só subir:
#   powershell -ExecutionPolicy Bypass -File .\dev-local.ps1
param([switch]$Preparar)
$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"

# As variáveis têm prioridade sobre o .env. Alembic/ETL usam a URL do dono: ambas devem ser locais.
$anteriores = @{}
foreach ($nome in @("DATABASE_URL", "DATABASE_URL_MIGRACOES", "MONGO_URI", "AMBIENTE")) {
  $anteriores[$nome] = [Environment]::GetEnvironmentVariable($nome, "Process")
}

function Garantir-Conteiner($nome, $argumentos) {
  if (-not (docker ps -a --format "{{.Names}}" | Select-String -SimpleMatch -Quiet $nome)) {
    docker run -d --name $nome @argumentos | Out-Null
  } else {
    docker start $nome | Out-Null
  }
  if ($LASTEXITCODE -ne 0) { throw "Não foi possível iniciar o contêiner local $nome." }
}
try {
  $env:DATABASE_URL = "postgresql+psycopg2://climasense:climasense@localhost:55433/climasense"
  $env:DATABASE_URL_MIGRACOES = $env:DATABASE_URL
  $env:MONGO_URI = "mongodb://localhost:27018/"
  $env:AMBIENTE = "desenvolvimento"
  Garantir-Conteiner "climasense-pg-dev" @("-e", "POSTGRES_USER=climasense", "-e", "POSTGRES_PASSWORD=climasense",
    "-e", "POSTGRES_DB=climasense", "-p", "55433:5432", "-v", "climasense-pg-dev:/var/lib/postgresql/data", "postgres:16-alpine")
  Garantir-Conteiner "climasense-mongo-dev" @("-p", "27018:27017", "-v", "climasense-mongo-dev:/data/db", "mongo:7")

  if ($Preparar) {
    Start-Sleep -Seconds 5
    Push-Location (Join-Path $raiz "backend")
    try {
      & (Join-Path $raiz ".venv\Scripts\alembic.exe") upgrade head
      if ($LASTEXITCODE -ne 0) { throw "As migrações locais falharam." }
      & $python -m climasense.territorio carregar
      if ($LASTEXITCODE -ne 0) { throw "A carga territorial local falhou." }
      & $python -m climasense.etl atualizar
      if ($LASTEXITCODE -ne 0) { throw "A atualização local terminou com falhas." }
    } finally { Pop-Location }
  }

  & (Join-Path $raiz "dev.ps1")
} finally {
  foreach ($nome in $anteriores.Keys) {
    [Environment]::SetEnvironmentVariable($nome, $anteriores[$nome], "Process")
  }
}
