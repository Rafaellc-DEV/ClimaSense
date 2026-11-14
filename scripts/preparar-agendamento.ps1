# Sem -Registrar, apenas valida a definição e mostra o plano. Não executa o ETL.
# Usar -Registrar somente depois da autorização para implantação descrita em docs/operacao-etl.md.
param([switch]$Registrar, [switch]$PermitirRemoto)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$script = Join-Path $PSScriptRoot "atualizar-operacional.ps1"
$argumentos = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $script + '"'
if ($PermitirRemoto) { $argumentos += " -PermitirRemoto" }
$acao = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argumentos -WorkingDirectory $raiz
$gatilho = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes 15)
$opcoes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3)
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$tarefa = New-ScheduledTask -Action $acao -Trigger $gatilho -Settings $opcoes -Principal $principal
$nome = "ClimaSense-ETL-Operacional"
if ($Registrar) {
  if (Get-ScheduledTask -TaskName $nome -ErrorAction SilentlyContinue) { throw "Já existe uma tarefa com esse nome; revise antes de substituir." }
  Register-ScheduledTask -TaskName $nome -InputObject $tarefa | Out-Null
}
[ordered]@{ tarefa = $nome; intervalo_min = 15; concorrencia = "IgnoreNew"; remoto = [bool]$PermitirRemoto; registrada = [bool]$Registrar; exige_usuario_conectado = $true } | ConvertTo-Json -Compress
