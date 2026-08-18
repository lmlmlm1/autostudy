@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
title AutoStudy 설정 변경

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [안내] 먼저 '설치하기.cmd'를 더블클릭해 설치를 완료하세요.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "chobo\처음_설정하기.py"
if errorlevel 1 (
    echo.
    echo [오류] 설정 창을 열거나 저장하지 못했습니다. 위 안내를 확인하세요.
    echo.
    pause
)
endlocal
