@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul && (py -3 translator.py & goto :end)
where python >nul 2>nul && (python translator.py & goto :end)
echo.
echo [!] 파이썬이 설치되어 있지 않습니다.
echo     https://www.python.org/downloads/ 에서 설치하세요.
echo     설치 첫 화면 맨 아래 "Add python.exe to PATH" 를 꼭 체크하세요.
start https://www.python.org/downloads/
:end
pause
