@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
title AutoStudy 복습 PDF 합치기

if not exist ".venv\Scripts\python.exe" goto not_installed

".venv\Scripts\python.exe" "chobo\처음_설정하기.py" --check
if errorlevel 1 goto not_configured

echo.
echo ============================================================
echo  날짜별 복습 PDF를 합칩니다.
echo  예: 1월 23일이면 0123을 입력하세요.
echo ============================================================
echo.
".venv\Scripts\python.exe" utility\merge_pdf.py
if errorlevel 1 goto merge_failed

echo.
echo 합본 작업을 마쳤습니다. 작업 폴더의 merged 폴더를 확인하세요.
goto finish

:not_installed
echo.
echo [안내] 먼저 chobo 폴더의 '설치하기.cmd'를 더블클릭해 설치를 완료하세요.
goto finish

:not_configured
echo.
echo [안내] 먼저 chobo 폴더의 '설정_변경하기.cmd'에서 최초 설정을 완료하세요.
goto finish

:merge_failed
echo.
echo [오류] 합본을 만들지 못했습니다. 위 창 전체를 캡처해 전달하세요.

:finish
echo.
pause
endlocal
