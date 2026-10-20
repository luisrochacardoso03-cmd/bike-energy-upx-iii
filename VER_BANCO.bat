@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 ver_banco.py
  pause
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python ver_banco.py
  pause
  exit /b
)
echo Python 3.11 ou superior nao encontrado.
pause
