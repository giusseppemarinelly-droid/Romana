# ============================================================
# main.py — Punto de entrada principal del sistema
# ============================================================
# Este es el archivo que ejecutas para iniciar el programa:
#   python main.py
#
# Hace 3 cosas:
#   1. Inicializa la base de datos (crea tablas si no existen)
#   2. Inicializa el display de pesaje (simulador por defecto)
#   3. Lanza la interfaz gráfica

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
    # PASO 1: Inicializar base de datos
    # -------------------------------------------------------
    print("\n📦 Iniciando base de datos...")
    try:
        from database.seed import inicializar_base_de_datos
        inicializar_base_de_datos()
    except Exception as e:
        print(f"❌ Error crítico en base de datos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


    # -------------------------------------------------------
    # PASO 2: Inicializar display de pesaje
    # -------------------------------------------------------
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
    # PASO 3: Lanzar interfaz gráfica
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
