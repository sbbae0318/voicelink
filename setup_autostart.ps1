# VoiceLink 자동 시작 설정 스크립트
# 관리자 권한으로 실행하세요.

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $scriptPath ".venv\Scripts\pythonw.exe"
$serviceScript = Join-Path $scriptPath "voicelink_service.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VoiceLink 자동 시작 설정" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Docker Desktop 자동 시작 확인
Write-Host "[1/3] Docker Desktop 자동 시작 확인..." -ForegroundColor Yellow
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$startupFolder = [Environment]::GetFolderPath("Startup")
$dockerShortcut = Join-Path $startupFolder "Docker Desktop.lnk"

if (Test-Path $dockerPath) {
    if (-not (Test-Path $dockerShortcut)) {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($dockerShortcut)
        $Shortcut.TargetPath = $dockerPath
        $Shortcut.Save()
        Write-Host "  ✅ Docker Desktop 시작 프로그램에 추가됨" -ForegroundColor Green
    }
    else {
        Write-Host "  ✅ Docker Desktop 이미 시작 프로그램에 있음" -ForegroundColor Green
    }
}
else {
    Write-Host "  ⚠️ Docker Desktop을 찾을 수 없음" -ForegroundColor Yellow
}

# 2. VoiceLink 서비스 작업 스케줄러 등록
Write-Host ""
Write-Host "[2/3] VoiceLink 녹음 서비스 작업 스케줄러 등록..." -ForegroundColor Yellow

$taskName = "VoiceLink Recording Service"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "  기존 작업 삭제 중..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# 작업 생성
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $serviceScript `
    -WorkingDirectory $scriptPath

$trigger = New-ScheduledTaskTrigger -AtLogon
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 999

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "VoiceLink 상시 녹음 서비스 - 자동 실행"

Write-Host "  ✅ 작업 스케줄러에 등록됨" -ForegroundColor Green

# 3. Docker Compose 서비스 자동 시작 스크립트
Write-Host ""
Write-Host "[3/3] Docker Compose 자동 시작 스크립트 생성..." -ForegroundColor Yellow

$dockerStartScript = @"
# VoiceLink Docker 서비스 자동 시작
Start-Sleep -Seconds 30  # Docker Desktop 시작 대기
Set-Location "$scriptPath"
docker compose -f docker/docker-compose.yml up -d
"@

$dockerStartPath = Join-Path $startupFolder "Start-VoiceLink-Docker.ps1"
$dockerStartScript | Out-File -FilePath $dockerStartPath -Encoding UTF8
Write-Host "  ✅ Docker 자동 시작 스크립트 생성됨" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  설정 완료!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "다음 시스템 시작 시 자동으로 시작됩니다:" -ForegroundColor White
Write-Host "  1. Docker Desktop" -ForegroundColor Cyan
Write-Host "  2. Ollama LLM 서버 (Docker)" -ForegroundColor Cyan
Write-Host "  3. 웹 대시보드 (Docker, http://localhost:8000)" -ForegroundColor Cyan
Write-Host "  4. VoiceLink 녹음 서비스 (호스트)" -ForegroundColor Cyan
Write-Host ""
Write-Host "지금 바로 시작하려면:" -ForegroundColor Yellow
Write-Host "  1. docker compose -f docker/docker-compose.yml up -d" -ForegroundColor White
Write-Host "  2. python voicelink_service.py" -ForegroundColor White
Write-Host ""
