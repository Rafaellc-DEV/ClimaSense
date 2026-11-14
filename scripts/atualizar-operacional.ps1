# Executa UMA rodada; não registra tarefas nem instala serviços.
# Antes de usar -PermitirRemoto, seguir docs/operacao-etl.md e obter autorização.
param([switch]$PermitirRemoto)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Ambiente Python do projeto não encontrado." }
$argumentos = @("-m", "climasense.etl", "operacional")
if ($PermitirRemoto) { $argumentos += "--permitir-remoto" }
Push-Location $raiz
try {
  & $python @argumentos
  $codigo = $LASTEXITCODE
} finally { Pop-Location }
exit $codigo
