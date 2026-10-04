@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta run.bat para instalar las dependencias.
  exit /b 1
)
".venv\Scripts\python.exe" mcp_server.py
