@echo off
REM VoiceLink 상시 녹음 서비스 시작 스크립트
REM Windows 시작 시 자동 실행하려면 시작 프로그램에 추가하세요.

cd /d "%~dp0"

echo ============================================================
echo   VoiceLink Recording Service
echo ============================================================
echo.
echo 녹음을 시작합니다...
echo 종료하려면 Ctrl+C를 누르세요.
echo.

:loop
.venv\Scripts\python voicelink_service.py
echo.
echo 서비스가 중단되었습니다. 5초 후 재시작...
timeout /t 5 /nobreak > nul
goto loop
