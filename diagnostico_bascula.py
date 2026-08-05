# ============================================================
# diagnostico_bascula.py — Herramienta de diagnóstico de báscula
# ============================================================
# Se corre DIRECTO en la PC de la Romana, sin desconectar el
# cable serial DB9 de la báscula. Sirve para:
#
#   1. Listar los puertos COM que Windows detecta.
#   2. Probar la comunicación real con el display, mandando el
#      comando de pedir peso y mostrando la respuesta cruda (raw)
#      tal cual la manda el equipo -- así se puede confirmar si
#      coincide con el protocolo Toledo que ya está implementado
#      en hardware/display_toledo.py, o si el formato es distinto.
#
# Uso:
#   1. Si el software viejo (Bigsoft) está corriendo y usando el
#      puerto, hay que CERRARLO primero (no desconectar el cable,
#      solo cerrar el programa) para liberar el puerto serial --
#      solo un programa a la vez puede tenerlo abierto.
#   2. pip install pyserial   (si no está instalado)
#   3. python diagnostico_bascula.py
#   4. Copiar TODA la salida de la consola y pegarla en el chat.
#
# No requiere el resto del proyecto (no importa nada de database/
# ni backend/) para poder correrlo aislado en la PC de planta.
# ============================================================

import sys

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("ERROR: falta pyserial. Instalar con:  pip install pyserial")
    sys.exit(1)


def listar_puertos():
    print("=" * 60)
    print("PUERTOS COM DETECTADOS POR WINDOWS")
    print("=" * 60)
    puertos = list(serial.tools.list_ports.comports())
    if not puertos:
        print("(no se detectó ningún puerto COM -- revisar Administrador")
        print(" de dispositivos, sección 'Puertos (COM y LPT)')")
        return []
    for p in puertos:
        print(f"  {p.device}  -  {p.description}  (hwid: {p.hwid})")
    return [p.device for p in puertos]


def probar_puerto(puerto: str, baudrate: int, timeout: float = 2.0):
    print("-" * 60)
    print(f"Probando {puerto} a {baudrate} bps, 8N1, timeout={timeout}s")
    try:
        ser = serial.Serial(
            port=puerto,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
    except serial.SerialException as e:
        print(f"  ERROR al abrir el puerto: {e}")
        print("  (¿otro programa lo tiene abierto? ¿es el puerto correcto?)")
        return

    try:
        print("  Puerto abierto OK.")

        # Primero: escuchar varios segundos sin mandar nada, por si el
        # display transmite peso continuamente solo (streaming), sin
        # necesidad de comando -- algunos indicadores (ej. el que ya
        # usa Bigsoft en esta planta, configurado a 1000ms) mandan una
        # trama nueva sola cada cierto intervalo, en vez de responder
        # a un comando puntual.
        import time
        ser.reset_input_buffer()
        segundos_escucha = 6
        print(f"  Escuchando {segundos_escucha}s sin enviar nada "
              f"(por si el display transmite solo, línea por línea)...")
        fin = time.time() + segundos_escucha
        lineas = []
        while time.time() < fin:
            linea = ser.readline()
            if linea:
                lineas.append(linea)
                try:
                    texto = linea.decode("ascii", errors="replace")
                except Exception:
                    texto = ""
                print(f"    Línea recibida -> raw: {linea!r}   texto: {texto!r}")

        if not lineas:
            print("    (nada recibido en modo escucha pasiva -- el display no")
            print("     transmite solo, o el timeout por línea cortó antes de completarla)")

        # Ahora: mandar el comando estándar Toledo 'W\r\n' y ver qué responde,
        # por si el equipo SÍ necesita un comando explícito en vez de streaming.
        ser.reset_input_buffer()
        comando = b"W\r\n"
        print(f"  Enviando comando: {comando!r}")
        ser.write(comando)
        respuesta = ser.readline()
        print(f"  Respuesta cruda (raw bytes): {respuesta!r}")
        if respuesta:
            try:
                print(f"  Respuesta como texto: {respuesta.decode('ascii', errors='replace')!r}")
            except Exception:
                pass
        else:
            print("  (timeout -- no respondió nada a 'W\\r\\n')")

    finally:
        ser.close()
        print("  Puerto cerrado.")


if __name__ == "__main__":
    try:
        print("DIAGNÓSTICO DE BÁSCULA -- Sistema Romana (Sura de Venezuela)")
        print()
        puertos = listar_puertos()
        print()

        if len(sys.argv) > 1:
            puerto = sys.argv[1]
        elif puertos:
            puerto = input(f"Puerto a probar (Enter = {puertos[0]}): ").strip() or puertos[0]
        else:
            puerto = input("Puerto a probar (ej: COM3): ").strip()

        baud_input = input("Baudrate a probar (Enter = 9600): ").strip()
        baudrate = int(baud_input) if baud_input else 9600

        print()
        probar_puerto(puerto, baudrate)
        print()
        print("=" * 60)
        print("Copiar TODA esta salida y pegarla en el chat con Claude.")
        print("=" * 60)
    except Exception as e:
        print()
        print(f"ERROR inesperado: {e}")
    print()
    input("Presiona ENTER para cerrar esta ventana...")
