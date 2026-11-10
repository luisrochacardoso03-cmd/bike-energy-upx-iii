@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 server.py
) else (
  python server.py
)
echo.
echo Se houve um erro, instale o Python e marque Add Python to PATH.
pause
