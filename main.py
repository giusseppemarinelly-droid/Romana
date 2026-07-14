# ============================================================
# main.py — Punto de entrada principal del sistema
# ============================================================
# Este es el archivo que ejecutas para iniciar el programa:
#   python main.py
#
# Hace 3 cosas:
#   0. Se asegura de que el backend esté corriendo (lo arranca solo
#      si apunta a localhost y no responde)
#   1. Inicializa el display de pesaje (simulador por defecto)
#   2. Lanza la interfaz gráfica
#
# En producción, Romana y Centro de Costos son estaciones separadas
# que le hablan a un backend en otra máquina de la red (ver README.md,
# ROMANA_API_URL) — ahí el paso 0 no hace nada porque el backend no es
# local. El auto-arranque es para no tener que levantar dos procesos
# a mano en una sola máquina (desarrollo, pruebas de escritorio).

import os
import subprocess
import sys
import time
from urllib.parse import urlparse

# Forzar UTF-8 en Windows para evitar errores con caracteres especiales
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Aseguramos que Python encuentre los módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_proceso_backend = None  # subprocess.Popen del backend, solo si lo arrancamos nosotros


def _backend_responde(base_url: str) -> bool:
    import httpx
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/health", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def _asegurar_backend():
    """
    Evita el freeze clásico de abrir la GUI sin el backend corriendo:
    cada pantalla le habla al backend por HTTP y, sin servidor, cada
    llamada se cuelga hasta el timeout (client/api_client.py) antes de
    mostrar error -- se siente como que "todo está pegado" al navegar.

    Si el backend no responde y config.API_BASE_URL apunta a
    localhost, lo levantamos nosotros como subproceso. Si apunta a
    otra máquina (estación real en la red de la planta), no tocamos
    nada -- ahí el backend vive en el servidor, no en esta estación.
    """
    global _proceso_backend
    from config import API_BASE_URL

    if _backend_responde(API_BASE_URL):
        print(f"✅ Backend ya está corriendo en {API_BASE_URL}")
        return

    host = urlparse(API_BASE_URL).hostname
    if host not in ("localhost", "127.0.0.1", "::1"):
        print(f"⚠️  Backend no responde en {API_BASE_URL} (no es local -- iniciarlo en esa máquina con run_server.py)")
        return

    print(f"⚙️  Backend no responde en {API_BASE_URL}. Iniciándolo automáticamente...")
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    script_servidor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_server.py")
    _proceso_backend = subprocess.Popen([sys.executable, script_servidor], **kwargs)

    for _ in range(20):  # hasta ~10s -- uvicorn tarda poco en arrancar
        time.sleep(0.5)
        if _backend_responde(API_BASE_URL):
            print("✅ Backend iniciado correctamente")
            return

    print("⚠️  El backend no respondió a tiempo. Revisa la ventana del servidor que se abrió.")


def _detener_backend_si_lo_iniciamos():
    if _proceso_backend is not None and _proceso_backend.poll() is None:
        print("\n🛑 Cerrando backend...")
        _proceso_backend.terminate()


def main():
    """Función principal — punto de entrada del sistema."""
    print("=" * 60)
    print("  🚛 SISTEMA DE ROMANA PARA CAMIONES")
    print("=" * 60)

    # -------------------------------------------------------
    # PASO 0: Asegurar que el backend esté disponible
    # -------------------------------------------------------
    print("\n🌐 Verificando backend...")
    try:
        _asegurar_backend()
    except Exception as e:
        print(f"⚠️  No se pudo verificar/iniciar el backend: {e}. Continuando de todas formas...")

    # -------------------------------------------------------
    # PASO 1: Inicializar display de pesaje
    # -------------------------------------------------------
    # La base de datos ya NO se inicializa acá: esta es la estación GUI
    # (Romana o Centro de Costos), que le habla al backend por HTTP
    # (ver client/api_client.py) y no necesita conectividad directa a
    # Postgres. El backend (run_server.py) es quien crea las tablas al
    # arrancar — ver backend/main.py.
    print("\n⚖️  Iniciando display de pesaje...")
    try:
        from hardware.display_manager import inicializar_display
        from config import DISPLAY

        resultado = inicializar_display(
            marca=DISPLAY["marca"],    # "Simulador" durante desarrollo
            puerto=DISPLAY["puerto"],
            baudrate=DISPLAY["baudrate"]
        )

        if resultado["exito"]:
            print(f"✅ {resultado['mensaje']}")
        else:
            # Si no hay hardware, usar simulador automáticamente
            print(f"⚠️  {resultado['mensaje']}")
            print("   Usando simulador de pesaje como respaldo...")
            resultado_sim = inicializar_display(marca="Simulador")
            if not resultado_sim["exito"]:
                print("❌ Error iniciando simulador")

    except Exception as e:
        print(f"⚠️  Error iniciando display: {e}. Continuando sin display...")

    # -------------------------------------------------------
    # PASO 2: Lanzar interfaz gráfica
    # -------------------------------------------------------
    print("\n🖥️  Iniciando interfaz gráfica...")
    try:
        from gui.app import App
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"❌ Error en interfaz gráfica: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        _detener_backend_si_lo_iniciamos()


if __name__ == "__main__":
    main()
