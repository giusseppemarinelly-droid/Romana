# ============================================================
# services/pesaje_service.py — Lógica del proceso de pesaje
# ============================================================
# FLUJO COMPLETO (nuevo):
#   1. ENTRADA: Camión llega → se pesa → estado "en_planta"
#   2. CAPTURA:  Camión cargado vuelve → 2° peso → "pendiente_aprobacion"
#   3. APROBACION: CC aprueba → "aprobado" / rechaza → "rechazado"
#   4. COMPLETAR: Romana llena datos finales → "completado"

from datetime import datetime
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from config import BASCULA
from database.engine import SessionLocal
from database.models import Pesada, Configuracion, Usuario


# ============================================================
# HELPER: cargar relaciones de Pesada
# ============================================================
# Hallazgo M-02 de la auditoría: acá había un _resolver_usuario_id()
# que era la función identidad (return usuario_id, nada más) -- su
# propio docstring explicaba que ya no había nada que resolver desde
# que las transiciones de estado dejaron de depender de un "usuario
# logueado" a nivel de proceso. Era indirección pura, hacía parecer que
# existía una regla donde no la había. Los 7 llamadores usan usuario_id
# directo ahora.


def _pesada_options():
    return [
        joinedload(Pesada.vehiculo),
        joinedload(Pesada.conductor),
        joinedload(Pesada.producto),
        joinedload(Pesada.proveedor),
        joinedload(Pesada.transportista),
        joinedload(Pesada.destino),
        joinedload(Pesada.lote),
        joinedload(Pesada.remolque),
        joinedload(Pesada.contenedor),
        joinedload(Pesada.usuario_entrada),
        joinedload(Pesada.usuario_salida),
        joinedload(Pesada.aprobado_por),
        joinedload(Pesada.usuario_completado),
        joinedload(Pesada.anulado_por),
    ]


# ============================================================
# CONFIGURACIÓN
# ============================================================
def _get_config(db, clave: str, default: str = "0") -> str:
    cfg = db.query(Configuracion).filter_by(clave=clave).first()
    return cfg.valor if cfg else default


def _set_config(db, clave: str, valor: str):
    cfg = db.query(Configuracion).filter_by(clave=clave).first()
    if cfg:
        cfg.valor = valor
    else:
        db.add(Configuracion(clave=clave, valor=valor))
    db.commit()


def _validar_rango_peso(peso: float) -> Optional[str]:
    """
    Hallazgo I-03: los límites físicos declarados en config.BASCULA
    (capacidad_max/capacidad_min) no se usaban en ningún lado -- cada
    captura validaba contra un 200 escrito a mano y nada validaba el
    techo. Una trama corrupta que parseara a un peso absurdo (ej.
    999.999 kg) entraba al sistema igual. Devuelve el mensaje de error,
    o None si el peso es válido.
    """
    if peso < BASCULA["capacidad_min"]:
        return (f"Peso muy bajo para un camión ({peso:,.0f} KG). "
                f"Mínimo configurado: {BASCULA['capacidad_min']:,.0f} KG. Verifique la báscula.")
    if peso > BASCULA["capacidad_max"]:
        return (f"Peso excede la capacidad de la báscula ({peso:,.0f} KG). "
                f"Máximo configurado: {BASCULA['capacidad_max']:,.0f} KG. Verifique la lectura.")
    return None


def generar_numero_ticket(db) -> str:
    """
    Hallazgo I-01: antes esto era un read-modify-write sin bloqueo, y
    _set_config() hacía su propio commit() DENTRO de la transacción de
    registrar_entrada() -- dos entradas concurrentes podían leer el mismo
    "ticket_actual" y generar el mismo número de ticket (UNIQUE), y si la
    entrada fallaba después, el contador ya había avanzado igual (hueco
    en una numeración fiscal).

    Ahora usa with_for_update(): la fila de configuracion queda bloqueada
    hasta que termine la transacción del caller (registrar_entrada() hace
    el único commit(), no acá) -- una segunda transacción concurrente
    espera a que la primera termine antes de leer "ticket_actual", así
    que nunca ven el mismo valor. En SQLite (tests) with_for_update() es
    no-op -- no hace falta ahí, la base entera se serializa a nivel de
    archivo.
    """
    prefijo = _get_config(db, "prefijo_ticket", "TK")
    cfg = db.query(Configuracion).filter_by(clave="ticket_actual").with_for_update().first()
    ultimo = int(cfg.valor) if cfg else 0
    nuevo_numero = ultimo + 1
    if cfg:
        cfg.valor = str(nuevo_numero)
    else:
        db.add(Configuracion(clave="ticket_actual", valor=str(nuevo_numero)))
    return f"{prefijo}-{nuevo_numero:06d}"


# ============================================================
# CONSULTAS DE ESTADO
# ============================================================
# Hallazgo M-01 de la auditoría (2026-09-14): esta sección tenía antes
# un bloque "MAESTROS" -- buscar_vehiculo_por_placa() y ocho
# listar_*_activos()/listar_productos_por_tipo() -- con cero llamadores
# en todo el repositorio (confirmado con grep antes de borrar, como
# pedía la auditoría). Reemplazadas hace tiempo por el CRUD genérico de
# backend/routers/maestros.py (crear_router_maestro()), que es lo que la
# GUI usa de verdad para estos maestros.
def listar_pesadas_en_planta() -> list:
    """Camiones que entraron y están esperando ser cargados."""
    db = SessionLocal()
    try:
        return db.query(Pesada).options(*_pesada_options()).filter(
            Pesada.estado == "en_planta",
            Pesada.anulada == False
        ).order_by(Pesada.fecha_entrada.desc()).all()
    finally:
        db.close()


def listar_pendientes_aprobacion() -> list:
    """Pesadas capturadas esperando aprobación de Centro de Costos."""
    db = SessionLocal()
    try:
        return db.query(Pesada).options(*_pesada_options()).filter(
            Pesada.estado == "pendiente_aprobacion",
            Pesada.anulada == False
        ).order_by(Pesada.fecha_captura.desc()).all()
    finally:
        db.close()


def listar_auto_aprobadas_recientes(limit: int = 30) -> list:
    """
    Pesadas que se aprobaron solas por estar la diferencia peso_guia/
    peso_neto dentro de tolerancia (ver capturar_peso_salida) --
    visibilidad de solo lectura para Centro de Costos, que no tuvo
    que decidir nada sobre ellas.
    """
    db = SessionLocal()
    try:
        return db.query(Pesada).options(*_pesada_options()).filter(
            Pesada.estado == "aprobado",
            Pesada.auto_aprobado == True,
            Pesada.anulada == False
        ).order_by(Pesada.fecha_aprobacion.desc()).limit(limit).all()
    finally:
        db.close()


def listar_aprobadas_pendientes_completar() -> list:
    """Pesadas que CC aprobó pero Romana aún no ha completado los datos."""
    db = SessionLocal()
    try:
        return db.query(Pesada).options(*_pesada_options()).filter(
            Pesada.estado == "aprobado",
            Pesada.anulada == False
        ).order_by(Pesada.fecha_aprobacion.desc()).all()
    finally:
        db.close()


def listar_pesadas_completadas(limit: int = 100) -> list:
    db = SessionLocal()
    try:
        return db.query(Pesada).options(*_pesada_options()).filter(
            Pesada.estado == "completado",
            Pesada.anulada == False
        ).order_by(Pesada.fecha_salida.desc()).limit(limit).all()
    finally:
        db.close()


def obtener_estadisticas_dashboard() -> dict:
    """
    Métricas del dashboard, agregadas en SQL (COUNT/SUM) en vez de
    traer las filas completas con sus relaciones como hace
    listar_pesadas_completadas() -- esa función existe para el kardex,
    que sí necesita las filas enteras; el dashboard solo necesita
    cuatro números y no debería bajar por red cientos de registros
    (creciendo indefinidamente con el tiempo) solo para contarlos.
    """
    db = SessionLocal()
    try:
        en_planta = db.query(func.count(Pesada.id)).filter(
            Pesada.estado == "en_planta", Pesada.anulada == False
        ).scalar() or 0

        hoy = datetime.now().date()
        completadas_hoy, neto_hoy = db.query(
            func.count(Pesada.id), func.coalesce(func.sum(Pesada.peso_neto), 0)
        ).filter(
            Pesada.estado == "completado",
            Pesada.anulada == False,
            func.date(Pesada.fecha_salida) == hoy,
        ).one()

        total_completadas = db.query(func.count(Pesada.id)).filter(
            Pesada.estado == "completado", Pesada.anulada == False
        ).scalar() or 0

        return {
            "en_planta": en_planta,
            "completadas_hoy": completadas_hoy or 0,
            "neto_hoy_kg": float(neto_hoy or 0),
            "total_completadas": total_completadas,
        }
    finally:
        db.close()


def get_pesada_en_planta_por_vehiculo(vehiculo_id: int) -> Optional[Pesada]:
    db = SessionLocal()
    try:
        return db.query(Pesada).options(*_pesada_options()).filter(
            Pesada.vehiculo_id == vehiculo_id,
            Pesada.estado.in_(["en_planta", "pendiente_aprobacion", "aprobado", "rechazado"]),
            Pesada.anulada == False
        ).first()
    finally:
        db.close()


# ============================================================
# PASO 1: REGISTRO DE ENTRADA
# ============================================================
def registrar_entrada(
    peso_bruto: float,
    vehiculo_id: int,
    tipo_pesaje: str = "GENERAL",
    producto_id: Optional[int] = None,
    empresa_transportista: str = "",
    empresa_cliente_proveedor: str = "",
    conductor_id: Optional[int] = None,
    cedula_conductor_libre: str = "",
    proveedor_id: Optional[int] = None,
    empresa_transportista_id: Optional[int] = None,
    destino_id: Optional[int] = None,
    lote_id: Optional[int] = None,
    remolque_id: Optional[int] = None,
    contenedor_id: Optional[int] = None,
    observaciones: str = "",
    procedencia: str = "",
    es_manual: bool = False,
    usuario_id: Optional[int] = None
) -> dict:
    """
    PASO 1: Registra la entrada del camión a la báscula.
    Captura el primer peso (camión vacío o camión lleno antes de descargar).
    Estado resultante: "en_planta"
    """
    db = SessionLocal()
    try:
        if peso_bruto <= 0:
            return {"exito": False, "mensaje": "El peso debe ser mayor a 0"}
        error_rango = _validar_rango_peso(float(peso_bruto))
        if error_rango:
            return {"exito": False, "mensaje": error_rango}

        # Verificar si el vehículo ya tiene una pesada activa
        activa = db.query(Pesada).filter(
            Pesada.vehiculo_id == vehiculo_id,
            Pesada.estado.in_(["en_planta", "pendiente_aprobacion", "aprobado", "rechazado"]),
            Pesada.anulada == False
        ).first()

        if activa:
            return {
                "exito": False,
                "mensaje": f"El vehículo ya tiene una pesada activa (Ticket: {activa.numero_ticket}, Estado: {activa.estado}). "
                           f"Debe completar o anular esa operación primero."
            }

        # Reintento acotado: with_for_update() en generar_numero_ticket()
        # cierra la colisión de numero_ticket de verdad en Postgres (el
        # motor real, un solo intento alcanza), pero en SQLite (dialecto
        # de los tests) es un no-op -- ahí la colisión sigue siendo
        # posible bajo concurrencia, y con contención alta (8 hilos
        # peleando la misma fila sin lock real) a veces hacen falta más
        # de 3 reintentos para que todos terminen consiguiendo un número
        # propio (confirmado con el test de concurrencia: con 3 fallaba
        # de forma intermitente). En vez de asumir a ciegas que todo
        # IntegrityError es "vehículo ya tiene pesada activa" (hallazgo
        # I-01: ese mensaje era falso cuando la causa real era una
        # colisión de ticket), se distingue por el texto del error y, si
        # fue el ticket, se reintenta con un número nuevo -- autocurativo,
        # no hace falta que el operador vuelva a intentar a mano.
        ultimo_error = None
        for _intento in range(10):
            numero_ticket = generar_numero_ticket(db)

            nueva_pesada = Pesada(
                numero_ticket=numero_ticket,
                estado="en_planta",
                tipo_pesaje=tipo_pesaje,
                fecha_entrada=datetime.now(),
                peso_entrada=round(float(peso_bruto), 2),
                peso_bruto=round(float(peso_bruto), 2),
                vehiculo_id=vehiculo_id,
                conductor_id=conductor_id,
                cedula_conductor_libre=cedula_conductor_libre.strip() if cedula_conductor_libre else None,
                producto_id=producto_id,
                proveedor_id=proveedor_id,
                empresa_transportista_id=empresa_transportista_id,
                destino_id=destino_id,
                lote_id=lote_id,
                remolque_id=remolque_id,
                contenedor_id=contenedor_id,
                empresa_transportista=empresa_transportista.strip() if empresa_transportista else None,
                empresa_cliente_proveedor=empresa_cliente_proveedor.strip() if empresa_cliente_proveedor else None,
                usuario_entrada_id=usuario_id,
                observaciones=observaciones,
                procedencia=procedencia.strip() if procedencia else None,
                es_manual=es_manual
            )

            db.add(nueva_pesada)
            try:
                db.commit()
                break
            except IntegrityError as e:
                db.rollback()
                # OJO: se clasifica por str(e.orig) -- el error crudo del
                # driver (sqlite3.IntegrityError / pg8000.dbapi.IntegrityError)
                # -- y NO por str(e), que es el wrapper de SQLAlchemy. Se
                # probaron ambas variantes con str(e) primero (buscando
                # "numero_ticket", después "vehiculo") y las dos fallaban
                # de la misma forma sutil: str(e) de SQLAlchemy incluye el
                # SQL completo del INSERT pegado al final
                # ("[SQL: INSERT INTO pesadas (numero_ticket, ..., vehiculo_id, ...)")],
                # así que CUALQUIER IntegrityError de este INSERT
                # "contiene" tanto "numero_ticket" como "vehiculo" en el
                # texto sin importar cuál restricción falló de verdad --
                # los nombres de columna están siempre ahí, en la lista de
                # columnas del INSERT. e.orig es el mensaje real y corto
                # del driver, sin el SQL pegado.
                mensaje_driver = str(e.orig).lower()

                # Vehículo activo: identificado por "vehiculo" en el
                # mensaje real -- portable entre dialectos (SQLite
                # reporta la columna "pesadas.vehiculo_id", Postgres el
                # nombre del índice "ux_pesada_activa_por_vehiculo"; no
                # coinciden exacto entre sí, pero ambos contienen
                # "vehiculo").
                if "vehiculo" in mensaje_driver:
                    return {
                        "exito": False,
                        "mensaje": "El vehículo ya tiene una pesada activa (detectado por la base de datos). Intente de nuevo."
                    }
                # Cualquier otra cosa (colisión de numero_ticket, o la
                # carrera de "configuracion.clave" cuando dos hilos crean
                # la fila "ticket_actual" por primera vez a la vez bajo
                # SQLite) se reintenta con un número nuevo.
                ultimo_error = e
                continue
        else:
            return {
                "exito": False,
                "mensaje": f"No se pudo generar un número de ticket único tras varios intentos: {ultimo_error}"
            }
        db.refresh(nueva_pesada)
        nueva_pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=nueva_pesada.id).first()

        return {
            "exito": True,
            "mensaje": f"Entrada registrada. Ticket: {numero_ticket}",
            "pesada": nueva_pesada,
            "ticket": numero_ticket
        }

    except Exception:
        # Hallazgo I-10: ya no se atrapa genérico para devolver
        # f"Error: {str(e)}" al cliente -- eso filtraba SQL/rutas del
        # servidor a la pantalla y enmascaraba bugs de programación como
        # si fueran errores de negocio. Lo que no se sabe manejar acá
        # sube tal cual; backend/main.py lo loguea completo del lado del
        # servidor y responde un 500 genérico sin detalles internos.
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
# PASO 2: CAPTURAR PESO DE SALIDA → va a Centro de Costos
# ============================================================
def capturar_peso_salida(
    pesada_id: int,
    peso_capturado: float,
    codigo_viaje: str,
    peso_guia: float,
    bultos: int,
    es_manual: bool = False,
    usuario_id: Optional[int] = None
) -> dict:
    """
    PASO 2: El camión volvió cargado, se captura el 2° peso junto con
    los datos de la guía del transportista (código de viaje, peso
    guía, bultos). Si la diferencia entre peso_guia y el neto
    resultante está dentro de la tolerancia configurada
    (tolerancia_aprobacion_pct, default 10%), la pesada se aprueba
    sola -- Centro de Costos no tiene que decidir nada, pero igual ve
    la pesada (de solo lectura, ver listar_auto_aprobadas_recientes).
    Si la diferencia supera la tolerancia, sigue el camino normal:
    va a la cola accionable de CC.
    Estado resultante: "aprobado" (auto) o "pendiente_aprobacion" (manual)
    """
    db = SessionLocal()
    try:
        pesada = db.query(Pesada).filter_by(id=pesada_id, anulada=False).first()

        if not pesada:
            return {"exito": False, "mensaje": "Pesada no encontrada"}

        if pesada.estado not in ["en_planta", "rechazado"]:
            return {
                "exito": False,
                "mensaje": f"No se puede capturar peso. Estado actual: {pesada.estado}"
            }

        if peso_capturado <= 0:
            return {"exito": False, "mensaje": "El peso debe ser mayor a 0"}
        error_rango = _validar_rango_peso(float(peso_capturado))
        if error_rango:
            return {"exito": False, "mensaje": error_rango}

        if not codigo_viaje or not codigo_viaje.strip():
            return {"exito": False, "mensaje": "Debe ingresar el código del viaje"}

        if peso_guia is None or peso_guia <= 0:
            return {"exito": False, "mensaje": "El peso guía debe ser mayor a 0"}

        if bultos is None or bultos <= 0:
            return {"exito": False, "mensaje": "La cantidad de bultos debe ser mayor a 0"}

        # Calcular neto preliminar (bruto mayor, tara menor). Contra
        # peso_entrada, NO contra peso_bruto -- peso_bruto se reescribe en
        # cada captura (incluida una re-captura tras un rechazo de CC) y
        # deja de representar la entrada real; peso_entrada se escribe una
        # sola vez en registrar_entrada() y nunca cambia (ver C-01).
        peso1 = float(pesada.peso_entrada)
        peso2 = float(peso_capturado)

        if peso2 > peso1:
            bruto_real = peso2
            tara_real = peso1
        else:
            bruto_real = peso1
            tara_real = peso2

        neto = round(bruto_real - tara_real, 2)
        diferencia_pct = round(abs(neto - float(peso_guia)) / float(peso_guia) * 100, 2)
        try:
            umbral = float(_get_config(db, "tolerancia_aprobacion_pct", "10"))
        except (ValueError, TypeError):
            # Hallazgo M-04: antes esto no tenía try -- un valor mal
            # escrito en la pantalla de Configuración (ej. "10,5" con
            # coma en vez de punto, texto libre sin validar) tumbaba
            # TODA captura de salida con un error genérico que no
            # apuntaba a la causa real. Con un valor inválido, se usa el
            # default documentado (10%) en vez de romper el flujo
            # completo por un typo en otra pantalla.
            umbral = 10.0
        auto_aprobado = diferencia_pct < umbral

        pesada.peso_tara = round(tara_real, 2)
        pesada.peso_bruto = round(bruto_real, 2)
        pesada.peso_neto = neto
        pesada.codigo_viaje = codigo_viaje.strip()
        pesada.peso_guia = round(float(peso_guia), 2)
        pesada.bultos = int(bultos)
        pesada.fecha_captura = datetime.now()
        pesada.motivo_rechazo = None  # Limpiar rechazo anterior si hubo
        pesada.usuario_salida_id = usuario_id
        pesada.es_manual = pesada.es_manual or es_manual

        if auto_aprobado:
            pesada.estado = "aprobado"
            pesada.auto_aprobado = True
            pesada.fecha_aprobacion = datetime.now()
            mensaje = (f"Peso capturado. Neto: {neto:,.0f} KG. Diferencia {diferencia_pct}% "
                       f"dentro de tolerancia: aprobado automáticamente.")
        else:
            pesada.estado = "pendiente_aprobacion"
            pesada.auto_aprobado = False
            mensaje = (f"Peso capturado. Neto: {neto:,.0f} KG. Diferencia {diferencia_pct}%: "
                       f"enviado a Centro de Costos para revisión.")

        db.commit()
        pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=pesada.id).first()

        return {
            "exito": True,
            "mensaje": mensaje,
            "pesada": pesada,
            "peso_neto": neto,
            "auto_aprobado": auto_aprobado,
            "diferencia_pct": diferencia_pct,
        }

    except Exception:
        db.rollback()  # ver comentario en registrar_entrada() -- hallazgo I-10
        raise
    finally:
        db.close()


# ============================================================
# PASO 3a: APROBAR (Centro de Costos)
# ============================================================
def aprobar_pesada(pesada_id: int, usuario_id: Optional[int] = None) -> dict:
    """
    PASO 3a: Centro de Costos aprueba la pesada.
    Estado resultante: "aprobado"
    """
    db = SessionLocal()
    try:
        pesada = db.query(Pesada).filter_by(id=pesada_id, anulada=False).first()

        if not pesada:
            return {"exito": False, "mensaje": "Pesada no encontrada"}

        if pesada.estado != "pendiente_aprobacion":
            return {
                "exito": False,
                "mensaje": f"Solo se pueden aprobar pesadas en estado 'pendiente_aprobacion'. Estado actual: {pesada.estado}"
            }

        pesada.estado = "aprobado"
        pesada.aprobado_por_id = usuario_id
        pesada.fecha_aprobacion = datetime.now()

        db.commit()
        pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=pesada.id).first()

        return {
            "exito": True,
            "mensaje": f"Pesada {pesada.numero_ticket} aprobada.",
            "pesada": pesada
        }

    except Exception:
        db.rollback()  # ver comentario en registrar_entrada() -- hallazgo I-10
        raise
    finally:
        db.close()


# ============================================================
# PASO 3b: RECHAZAR (Centro de Costos)
# ============================================================
def rechazar_pesada(pesada_id: int, motivo: str, usuario_id: Optional[int] = None) -> dict:
    """
    PASO 3b: Centro de Costos rechaza la pesada.
    Vuelve al estado "rechazado" — Romana debe volver a capturar.
    Estado resultante: "rechazado"
    """
    db = SessionLocal()
    try:
        pesada = db.query(Pesada).filter_by(id=pesada_id, anulada=False).first()

        if not pesada:
            return {"exito": False, "mensaje": "Pesada no encontrada"}

        if pesada.estado != "pendiente_aprobacion":
            return {
                "exito": False,
                "mensaje": f"Solo se pueden rechazar pesadas en estado 'pendiente_aprobacion'."
            }

        if not motivo or len(motivo.strip()) < 3:
            return {"exito": False, "mensaje": "Debe ingresar un motivo de rechazo"}

        pesada.estado = "rechazado"
        pesada.motivo_rechazo = motivo.strip()
        pesada.aprobado_por_id = usuario_id
        pesada.fecha_aprobacion = datetime.now()

        db.commit()

        return {
            "exito": True,
            "mensaje": f"Pesada {pesada.numero_ticket} rechazada. Romana debe volver a capturar.",
        }

    except Exception:
        db.rollback()  # ver comentario en registrar_entrada() -- hallazgo I-10
        raise
    finally:
        db.close()


# ============================================================
# PASO 4: COMPLETAR PESAJE (Romana, post-aprobación)
# ============================================================
def completar_pesaje(
    pesada_id: int,
    peso_final: float,
    orden_compra: str = "",
    cantidad: Optional[float] = None,
    precintos: str = "",
    observaciones: str = "",
    es_manual: bool = False,
    usuario_id: Optional[int] = None
) -> dict:
    """
    PASO 4: Romana captura el peso final (3er pesaje, antes de autorizar la
    salida), llena los datos finales y cierra la operación. Solo disponible
    después de que CC haya aprobado. El peso_final se registra sin validar
    tolerancia contra el pre-pesaje -- es un control informativo para el
    operador, no bloquea el cierre si difiere.
    Estado resultante: "completado"
    """
    db = SessionLocal()
    try:
        pesada = db.query(Pesada).filter_by(id=pesada_id, anulada=False).first()

        if not pesada:
            return {"exito": False, "mensaje": "Pesada no encontrada"}

        if pesada.estado != "aprobado":
            return {
                "exito": False,
                "mensaje": f"Solo se pueden completar pesadas aprobadas por CC. Estado: {pesada.estado}"
            }

        if peso_final <= 0:
            return {"exito": False, "mensaje": "El peso final debe ser mayor a 0"}
        error_rango = _validar_rango_peso(float(peso_final))
        if error_rango:
            return {"exito": False, "mensaje": error_rango}

        pesada.peso_final = round(float(peso_final), 2)
        pesada.orden_compra = orden_compra.strip() if orden_compra else None
        pesada.cantidad = round(float(cantidad), 2) if cantidad else None
        pesada.precintos = precintos.strip() if precintos else None
        # Hallazgo I-06: antes esto pisaba SIEMPRE las observaciones,
        # incluso con una cadena vacía -- borraba lo que se hubiera
        # cargado en la entrada. Ahora solo se actualiza si vino un valor.
        if observaciones:
            pesada.observaciones = observaciones.strip()
        pesada.estado = "completado"
        pesada.fecha_salida = datetime.now()
        # usuario_completado_id, NO usuario_salida_id -- son dos actos
        # distintos (capturar el 2° peso vs. completar el pesaje) y
        # pueden ser dos operadores de turnos distintos. Antes esto
        # reescribía usuario_salida_id, perdiendo quién había capturado
        # el 2° peso (hallazgo I-06).
        pesada.usuario_completado_id = usuario_id
        pesada.es_manual = pesada.es_manual or es_manual

        db.commit()
        pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=pesada.id).first()

        return {
            "exito": True,
            "mensaje": f"Pesada {pesada.numero_ticket} completada. Neto: {float(pesada.peso_neto):,.0f} KG",
            "pesada": pesada
        }

    except Exception:
        db.rollback()  # ver comentario en registrar_entrada() -- hallazgo I-10
        raise
    finally:
        db.close()


# ============================================================
# ANULACIÓN
# ============================================================
def anular_pesada(pesada_id: int, motivo: str, usuario_id: Optional[int] = None) -> dict:
    db = SessionLocal()
    try:
        pesada = db.query(Pesada).filter_by(id=pesada_id).first()
        if not pesada:
            return {"exito": False, "mensaje": "Pesada no encontrada"}
        if pesada.anulada:
            return {"exito": False, "mensaje": "La pesada ya está anulada"}
        if pesada.estado == "completado":
            # Mandato de integridad: un pesaje cerrado (completado) no se
            # puede alterar manualmente, ni siquiera para anularlo.
            return {"exito": False, "mensaje": "No se puede anular una pesada ya completada (registro cerrado e inmutable)"}
        if not motivo or len(motivo.strip()) < 5:
            return {"exito": False, "mensaje": "Debe ingresar un motivo de anulación (mínimo 5 caracteres)"}

        pesada.anulada = True
        pesada.estado = "anulado"
        pesada.motivo_anulacion = motivo.strip()
        # Hallazgo I-05: antes esto ni siquiera recibía usuario_id -- la
        # anulación, la operación más sensible del sistema después del
        # cierre, era la única transición de estado sin constancia de
        # quién la hizo.
        pesada.anulado_por_id = usuario_id
        pesada.fecha_anulacion = datetime.now()
        db.commit()

        return {"exito": True, "mensaje": f"Pesada {pesada.numero_ticket} anulada"}
    except Exception:
        db.rollback()  # ver comentario en registrar_entrada() -- hallazgo I-10
        raise
    finally:
        db.close()


# ============================================================
# CORTE
# ============================================================
def listar_cortes(limit: int = 20) -> list:
    from database.models import Corte
    db = SessionLocal()
    try:
        return db.query(Corte).order_by(Corte.id.desc()).limit(limit).all()
    finally:
        db.close()


def realizar_corte(observaciones: str = "", usuario_id: Optional[int] = None) -> dict:
    from database.models import Corte
    db = SessionLocal()
    try:
        ultimo_corte = db.query(Corte).order_by(Corte.id.desc()).first()
        fecha_inicio = ultimo_corte.fecha_fin if ultimo_corte else datetime(2000, 1, 1)
        fecha_fin = datetime.now()

        # Hallazgo M-03: el filtro anterior era >= fecha_inicio Y
        # <= fecha_fin, los dos inclusive -- una pesada cuyo fecha_salida
        # cayera EXACTO en el instante de corte pertenecía a los dos
        # períodos (el que termina ahí y el que empieza ahí), contada
        # dos veces entre este corte y el próximo. Límite superior
        # exclusivo: el instante exacto pasa a pertenecer solo al corte
        # que EMPIEZA ahí, no al que termina.
        pesadas = db.query(Pesada).filter(
            Pesada.estado == "completado",
            Pesada.anulada == False,
            Pesada.fecha_salida >= fecha_inicio,
            Pesada.fecha_salida < fecha_fin
        ).all()

        total_pesadas = len(pesadas)
        total_neto = sum(float(p.peso_neto or 0) for p in pesadas)

        ultimo_num = int(_get_config(db, "corte_actual", "0"))
        nuevo_num = ultimo_num + 1
        _set_config(db, "corte_actual", str(nuevo_num))

        nuevo_corte = Corte(
            numero_corte=nuevo_num,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_pesadas=total_pesadas,
            total_neto_kg=round(total_neto, 2),
            # Hallazgo M-03: antes "usuario_id or 1" atribuía el corte al
            # usuario 1 en silencio si faltaba el dato -- usuario_id no
            # debería faltar nunca (el router siempre pasa el del JWT),
            # y si algún día falta de verdad, es mejor que el commit()
            # falle fuerte (columna NOT NULL) a que quede mal atribuido.
            usuario_id=usuario_id,
            observaciones=observaciones,
            created_at=datetime.now()
        )
        db.add(nuevo_corte)
        db.commit()
        db.refresh(nuevo_corte)

        return {
            "exito": True,
            "mensaje": f"Corte #{nuevo_num} realizado",
            "corte": nuevo_corte,
            "total_pesadas": total_pesadas,
            "total_neto_kg": round(total_neto, 2),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }

    except Exception:
        db.rollback()  # ver comentario en registrar_entrada() -- hallazgo I-10
        raise
    finally:
        db.close()


# ============================================================
# KARDEX
# ============================================================
def get_kardex(
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    producto_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    vehiculo_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit: int = 500
) -> list:
    db = SessionLocal()
    try:
        query = db.query(Pesada).options(*_pesada_options())

        if fecha_inicio:
            query = query.filter(Pesada.fecha_entrada >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Pesada.fecha_entrada <= fecha_fin)
        if producto_id:
            query = query.filter(Pesada.producto_id == producto_id)
        if proveedor_id:
            query = query.filter(Pesada.proveedor_id == proveedor_id)
        if vehiculo_id:
            query = query.filter(Pesada.vehiculo_id == vehiculo_id)
        if estado:
            query = query.filter(Pesada.estado == estado)

        return query.order_by(Pesada.fecha_entrada.desc()).limit(limit).all()
    finally:
        db.close()
