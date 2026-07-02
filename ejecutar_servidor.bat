@echo off
REM ============================================================
REM ejecutar_servidor.bat — Inicia el backend (API + WebSockets)
REM ============================================================
REM Se corre UNA vez en la maquina "servidor". Las estaciones de
REM Romana y Centro de Costos (ejecutar.bat) le hablan por red.

cd /d "%~dp0"
call venv\Scripts\activate.bat
python run_server.py
pause
