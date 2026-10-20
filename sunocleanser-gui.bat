@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where conda >nul 2>&1
if errorlevel 1 (
  echo Error: conda no esta en el PATH. Crea el entorno sunocleanser primero.
  pause
  exit /b 1
)

conda run -n sunocleanser --no-capture-output python -m src.gui %*
exit /b %ERRORLEVEL%
