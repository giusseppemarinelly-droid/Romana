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

# Mismo arreglo que main.py: la consola de Windows usa cp1252 por defecto y
# rompe los acentos de esta salida, que es justo la que hay que leer y pegar.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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


def volcar_hex(linea: bytes) -> str:
    """
    Cada byte en hexadecimal junto a su carácter. Es lo que responde de verdad
    la pregunta del ancho del campo de peso: cuántos espacios (0x20) hay entre
    el signo y el primer dígito, y si el relleno es con espacios o con ceros.
    Mirando solo el texto, '+      0' y '+000000' se parecen demasiado.
    """
    partes = []
    for b in linea:
        car = chr(b) if 32 <= b < 127 else "·"
        partes.append(f"{b:02X}={car}")
    return "  ".join(partes)


def probar_puerto(puerto: str, baudrate: int, timeout: float = 2.0, segundos_escucha: int = 6):
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
                print(f"                      hex: {volcar_hex(linea)}")

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
            print(f"  Respuesta en hex: {volcar_hex(respuesta)}")
            try:
                print(f"  Respuesta como texto: {respuesta.decode('ascii', errors='replace')!r}")
            except Exception:
                pass
        else:
            print("  (timeout -- no respondió nada a 'W\\r\\n')")

    finally:
        ser.close()
        print("  Puerto cerrado.")


# Baudrates que vale la pena barrer si el configurado no devuelve nada legible.
# Un baudrate equivocado no da error: da bytes de basura o silencio, que es
# indistinguible de un cable malo si no se prueban otros.
BAUDRATES_COMUNES = [9600, 4800, 19200, 2400, 38400, 57600, 115200]


def _parsear_argumentos(argv):
    """
    Modo no interactivo si viene cualquier flag o si la entrada no es una
    consola (por ejemplo cuando lo lanza otro proceso): sin flags y con
    consola, sigue preguntando como siempre para poder usarlo a mano.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Diagnóstico de la báscula -- Sistema Romana",
        epilog="Sin argumentos y en una consola, pregunta puerto y baudrate.",
    )
    parser.add_argument("puerto", nargs="?", help="Puerto a probar (ej: COM4)")
    parser.add_argument("-b", "--baudrate", type=int, help="Baudrate (default 9600)")
    parser.add_argument("-s", "--segundos", type=int, default=6,
                        help="Segundos de escucha pasiva (default 6)")
    parser.add_argument("--barrer", action="store_true",
                        help=f"Probar todos los baudrates comunes: {BAUDRATES_COMUNES}")
    parser.add_argument("--listar", action="store_true",
                        help="Solo listar los puertos detectados y salir")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parsear_argumentos(sys.argv[1:])
    interactivo = sys.stdin.isatty() and len(sys.argv) == 1

    try:
        print("DIAGNÓSTICO DE BÁSCULA -- Sistema Romana (Sura de Venezuela)")
        print()
        puertos = listar_puertos()
        print()

        if args.listar:
            sys.exit(0)

        puerto = args.puerto
        if not puerto and interactivo:
            if puertos:
                puerto = input(f"Puerto a probar (Enter = {puertos[0]}): ").strip() or puertos[0]
            else:
                puerto = input("Puerto a probar (ej: COM3): ").strip()
        elif not puerto:
            puerto = puertos[0] if puertos else None

        if not puerto:
            print("No hay ningún puerto COM para probar.")
            print("Conectá el adaptador USB-serial y volvé a correr esto.")
            sys.exit(1)

        baudrate = args.baudrate
        if baudrate is None and interactivo:
            entrada = input("Baudrate a probar (Enter = 9600): ").strip()
            baudrate = int(entrada) if entrada else 9600
        elif baudrate is None:
            baudrate = 9600

        print()
        if args.barrer:
            for baud in BAUDRATES_COMUNES:
                probar_puerto(puerto, baud, segundos_escucha=args.segundos)
                print()
        else:
            probar_puerto(puerto, baudrate, segundos_escucha=args.segundos)

        print()
        print("=" * 60)
        print("Copiar TODA esta salida y pegarla en el chat con Claude.")
        print("=" * 60)
    except Exception as e:
        print()
        print(f"ERROR inesperado: {e}")
    print()
    if interactivo:
        input("Presiona ENTER para cerrar esta ventana...")
