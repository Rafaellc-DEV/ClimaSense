# Executa UMA rodada do `etl operacional` (todas as fontes, cada uma na sua cadência) e grava o resultado em
# logs\etl-operacional-AAAA-MM.log. Quem repete a cada 15 min é a tarefa criada por preparar-agendamento.ps1.
# -PermitirRemoto grava no Neon/Atlas do .env: use só com a autorização descrita em docs/operacao-etl.md.
param([switch]$PermitirRemoto)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Ambiente Python do projeto não encontrado." }
$argumentos = @("-m", "climasense.etl", "operacional")
if ($PermitirRemoto) { $argumentos += "--permitir-remoto" }
$pastaLogs = Join-Path $raiz "logs"
New-Item -ItemType Directory -Force -Path $pastaLogs | Out-Null
$log = Join-Path $pastaLogs ("etl-operacional-" + (Get-Date -Format "yyyy-MM") + ".log")
$env:PYTHONIOENCODING = "utf-8"
Push-Location (Join-Path $raiz "backend")
try {
  Add-Content -LiteralPath $log -Encoding utf8 -Value ("=== " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
  $ErrorActionPreference = "Continue"
  & $python @argumentos 2>&1 | ForEach-Object { "$_" } | Add-Content -LiteralPath $log -Encoding utf8
  $codigo = $LASTEXITCODE
  Add-Content -LiteralPath $log -Encoding utf8 -Value ("=== código de saída " + $codigo)
} finally { Pop-Location }
exit $codigo
