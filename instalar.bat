@echo off
REM ============================================================
REM instalar.bat — Instalador automático del Sistema de Romana
REM ============================================================
REM Ejecuta este archivo como ADMINISTRADOR una sola vez.
REM Instala todas las dependencias Python necesarias.

echo.
echo ====================================================
echo   INSTALADOR - SISTEMA DE ROMANA PARA CAMIONES
echo ====================================================
echo.

REM Verificar que Python esté instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado.
    echo.
    echo Por favor instala Python desde:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Marca "Add Python to PATH" durante la instalación
    echo.
    pause
    exit /b 1
)

echo Python detectado:
python --version
echo.

REM Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo ERROR al crear entorno virtual
    pause
    exit /b 1
)
echo Entorno virtual creado correctamente.
echo.

REM Activar entorno virtual e instalar dependencias
echo Instalando dependencias (puede tardar unos minutos)...
echo.
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR al instalar dependencias
    pause
    exit /b 1
)

echo.
echo ====================================================
echo   INSTALACION COMPLETADA EXITOSAMENTE
echo ====================================================
echo.
echo Para iniciar el sistema, ejecuta:
echo   ejecutar.bat
echo.
pause
