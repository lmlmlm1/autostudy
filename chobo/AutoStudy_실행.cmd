@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
title AutoStudy 강의 처리

if not exist ".venv\Scripts\python.exe" goto not_installed

".venv\Scripts\python.exe" "chobo\처음_설정하기.py" --check
if errorlevel 1 goto not_configured

echo.
echo ============================================================
echo  AutoStudy 처리를 시작합니다.
echo  창을 닫지 말고, 마지막 안내가 나올 때까지 기다리세요.
echo ============================================================
echo.
".venv\Scripts\python.exe" main.py
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" goto processing_failed

echo ============================================================
echo  처리를 마쳤습니다.
echo  첫 실행이면 _whisperkeyword.txt를 확인한 뒤 Colab 전사를 진행하세요.
echo  두 번째 실행이면 작업 폴더의 강의별 결과 폴더를 확인하세요.
echo ============================================================
goto finish

:not_installed
echo.
echo [안내] 아직 설치가 끝나지 않았습니다.
echo chobo 폴더의 '설치하기.cmd'를 더블클릭해 설치를 완료하세요.
goto finish

:not_configured
echo.
echo [안내] 최초 설정이 끝나지 않았습니다.
echo chobo 폴더의 '설정_변경하기.cmd'를 더블클릭해 작업 폴더, Gemini, Notion, Drive를 설정하세요.
goto finish

:processing_failed
echo [오류] 처리 중 문제가 생겼습니다. 위 창 전체를 캡처해 전달하세요.

:finish
echo.
pause
endlocal
