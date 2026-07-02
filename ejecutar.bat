@echo off
REM ============================================================
REM ejecutar.bat — Inicia el Sistema de Romana para Camiones
REM ============================================================

cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
pause
