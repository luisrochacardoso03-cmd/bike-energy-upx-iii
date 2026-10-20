@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 app.py
  pause
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python app.py
  pause
  exit /b
)
echo Python 3.11 ou superior nao encontrado.
echo Instale pelo site oficial python.org e abra este arquivo novamente.
pause
