# ============================================================
# main.py — Punto de entrada principal del sistema
# ============================================================
# Este es el archivo que ejecutas para iniciar el programa:
#   python main.py
#
# Hace 2 cosas:
#   1. Inicializa el display de pesaje (simulador por defecto)
#   2. Lanza la interfaz gráfica
#
# Requiere que el backend ya esté corriendo (`python run_server.py`,
# ver README.md) — esta GUI le habla por HTTP/WebSocket, no toca la
# base de datos directamente.

import sys
import os

# Forzar UTF-8 en Windows para evitar errores con caracteres especiales
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Aseguramos que Python encuentre los módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Función principal — punto de entrada del sistema."""
    print("=" * 60)
    print("  🚛 SISTEMA DE ROMANA PARA CAMIONES")
    print("=" * 60)

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


if __name__ == "__main__":
    main()
