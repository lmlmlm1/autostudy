@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
title AutoStudy 설치

echo.
echo ============================================================
echo  AutoStudy 설치를 시작합니다.
echo  처음 설치하면 다운로드 때문에 시간이 걸릴 수 있습니다.
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto install_packages

where py >nul 2>nul
if not errorlevel 1 (
    echo Python 가상환경을 만드는 중입니다...
    py -3.11 -m venv .venv 2>nul
    if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
) else (
    where python >nul 2>nul
    if errorlevel 1 goto python_missing
    echo Python 가상환경을 만드는 중입니다...
    python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" goto venv_failed

:install_packages
echo.
echo 필요한 라이브러리를 설치 또는 업데이트합니다...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto pip_failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto dependency_failed

echo.
echo ============================================================
echo  설치가 완료되었습니다.
echo  chobo 폴더의 '설정_변경하기.cmd'를 더블클릭해 주세요.
echo ============================================================
goto finish

:python_missing
echo.
echo [오류] Python을 찾을 수 없습니다.
echo 1. https://www.python.org/downloads/windows/ 에서 Python 3.11을 설치하세요.
echo 2. 설치 화면에서 'Add python.exe to PATH'를 반드시 체크하세요.
echo 3. 설치가 끝나면 이 파일을 다시 더블클릭하세요.
goto finish

:venv_failed
echo.
echo [오류] Python 가상환경을 만들지 못했습니다.
echo Python 3.11을 설치한 뒤 다시 시도하세요.
goto finish

:pip_failed
echo.
echo [오류] pip 업데이트에 실패했습니다. 인터넷 연결을 확인한 뒤 다시 시도하세요.
goto finish

:dependency_failed
echo.
echo [오류] 필요한 라이브러리 설치에 실패했습니다.
echo 오류 화면 전체를 캡처해서 설정을 도와주는 사람에게 전달하세요.
goto finish

:finish
echo.
pause
endlocal
