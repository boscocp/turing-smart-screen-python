# Instala este fork como o monitor da tela Turing em uma maquina Windows nova
# (ou depois de formatar). Roda tudo: venv, dependencias, config pessoal, tema
# customizado, tarefa agendada elevada e atalho na Area de Trabalho.
#
# Uso: clique com o botao direito neste arquivo -> "Executar com o PowerShell"
#      (ou:  powershell -ExecutionPolicy Bypass -File .\meu-setup\instalar.ps1)
#
# Ele pede elevacao sozinho - a tarefa agendada precisa rodar como admin.

$ErrorActionPreference = 'Stop'

$TASK_NAME = 'Turing Sistema da Tela'
$SETUP_DIR = $PSScriptRoot
$REPO      = Split-Path $PSScriptRoot -Parent

# ---------------------------------------------------------------- elevacao ---
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host 'Pedindo elevacao (a tarefa agendada precisa de admin)...'
    Start-Process powershell -Verb RunAs -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`""
    )
    exit
}

Write-Host "Repositorio: $REPO" -ForegroundColor Cyan

# ------------------------------------------------------------------- python ---
$python = $null
foreach ($cand in @('py', 'python')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source; break }
}
if (-not $python) {
    throw 'Python nao encontrado no PATH. Instale o Python 3.9+ (3.13 e o usado aqui) e rode de novo.'
}

# --------------------------------------------------------------------- venv ---
$venvPy  = Join-Path $REPO 'venv\Scripts\python.exe'
$venvPyw = Join-Path $REPO 'venv\Scripts\pythonw.exe'

if (-not (Test-Path $venvPy)) {
    Write-Host 'Criando o venv...' -ForegroundColor Cyan
    if ($python -match '\\py\.exe$') {
        & $python -3 -m venv (Join-Path $REPO 'venv')
    } else {
        & $python -m venv (Join-Path $REPO 'venv')
    }
} else {
    Write-Host 'venv ja existe, reaproveitando.'
}

Write-Host 'Instalando dependencias (requirements.txt)...' -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r (Join-Path $REPO 'requirements.txt')

# ----------------------------------------------- config pessoal + tema ---
$destConfig = Join-Path $REPO 'config.yaml'
$destTheme  = Join-Path $REPO 'res\themes\LandscapeMagicBlue\theme.yaml'
$stamp      = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach ($par in @(
    @{ src = Join-Path $SETUP_DIR 'config.yaml';                    dst = $destConfig },
    @{ src = Join-Path $SETUP_DIR 'theme-LandscapeMagicBlue.yaml';  dst = $destTheme  }
)) {
    if (Test-Path $par.dst) {
        Copy-Item $par.dst "$($par.dst).bak-$stamp" -Force
    }
    Copy-Item $par.src $par.dst -Force
    Write-Host "Copiado: $($par.dst)"
}

# skip-worktree: impede que a config pessoal apareca como modificacao e vaze
# para um PR upstream (e que um checkout a sobrescreva).
Push-Location $REPO
try {
    git update-index --skip-worktree config.yaml
    git update-index --skip-worktree res/themes/LandscapeMagicBlue/theme.yaml
    Write-Host 'skip-worktree aplicado em config.yaml e theme.yaml'
} catch {
    Write-Warning "Nao consegui aplicar skip-worktree: $_"
} finally {
    Pop-Location
}

# ---------------------------------------------------------- tarefa agendada ---
Write-Host "Registrando a tarefa agendada '$TASK_NAME'..." -ForegroundColor Cyan

$action = New-ScheduledTaskAction -Execute $venvPyw -Argument 'main.py' -WorkingDirectory $REPO

$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Delay = 'PT30S'   # da tempo do USB/COM aparecer depois do logon

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Highest   # Highest e OBRIGATORIO (LibreHardwareMonitor)

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 72) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

# ----------------------------------------------------------------- atalho ---
$lnk  = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Turing Smart Screen.lnk'
$vbs  = Join-Path $SETUP_DIR 'reiniciar-turing.vbs'
$icon = Join-Path $REPO 'res\icons\monitor-icon-17865\icon.ico'

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($lnk)
$sc.TargetPath       = "$env:WINDIR\System32\wscript.exe"
$sc.Arguments        = "`"$vbs`""
$sc.WorkingDirectory = $REPO
$sc.IconLocation     = "$icon,0"
$sc.Description      = 'Reinicia o monitor da tela Turing (mata a instancia travada e sobe de novo)'
$sc.WindowStyle      = 7
$sc.Save()
Write-Host "Atalho criado: $lnk"

# ------------------------------------------------------------------ subir ---
Write-Host 'Subindo o monitor...' -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TASK_NAME
Start-Sleep -Seconds 12

$log = Join-Path $REPO 'log.log'
if (Test-Path $log) {
    Write-Host "`nUltimas linhas do log:" -ForegroundColor Cyan
    Get-Content $log -Tail 8
}

Write-Host "`nPronto. Se a tela nao acender, veja $log" -ForegroundColor Green
Write-Host 'Enter para fechar.'
[void](Read-Host)
