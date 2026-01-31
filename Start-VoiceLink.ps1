# VoiceLink 상시 녹음 서비스 시작 스크립트 (PowerShell)
# Windows 시작 시 자동 실행하려면 작업 스케줄러에 등록하세요.

$ErrorActionPreference = "Continue"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VoiceLink Recording Service" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "녹음을 시작합니다..." -ForegroundColor Green
Write-Host "종료하려면 Ctrl+C를 누르세요." -ForegroundColor Yellow
Write-Host ""

# 무한 재시작 루프
while ($true) {
    try {
        & .\.venv\Scripts\python.exe voicelink_service.py
    } catch {
        Write-Host "오류 발생: $_" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "서비스가 중단되었습니다. 5초 후 재시작..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}
