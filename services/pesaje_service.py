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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from database.engine import SessionLocal
from database.models import (
    Pesada, Vehiculo, Conductor, Producto,
    Proveedor, Destino, Lote, Remolque, Contenedor,
    Configuracion, Usuario
)
from services.auth_service import get_usuario_actual


# ============================================================
# HELPER: cargar relaciones de Pesada
# ============================================================
def _resolver_usuario_id(usuario_id: Optional[int]) -> Optional[int]:
    """
    Resuelve qué usuario_id usar en una transición de estado.

    Backend HTTP: pasa `usuario_id` explícito (viene del JWT vía
    `Depends(get_current_user)`) — cada request es de un usuario distinto,
    no hay estado global que consultar.

    GUI vieja (no migrada aún): no pasa `usuario_id`, así que se cae al
    global `_usuario_actual` de `auth_service` por compatibilidad. Se
    elimina este fallback cuando termine la fase de limpieza de la
    migración a cliente-servidor.
    """
    if usuario_id is not None:
        return usuario_id
    usuario = get_usuario_actual()
    return usuario.id if usuario else None


def _pesada_options():
    return [
        joinedload(Pesada.vehiculo),
        joinedload(Pesada.conductor),
        joinedload(Pesada.producto),
        joinedload(Pesada.proveedor),
        joinedload(Pesada.destino),
        joinedload(Pesada.lote),
        joinedload(Pesada.remolque),
        joinedload(Pesada.contenedor),
        joinedload(Pesada.usuario_entrada),
        joinedload(Pesada.usuario_salida),
        joinedload(Pesada.aprobado_por),
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


def generar_numero_ticket(db) -> str:
    prefijo = _get_config(db, "prefijo_ticket", "TK")
    ultimo = int(_get_config(db, "ticket_actual", "0"))
    nuevo_numero = ultimo + 1
    _set_config(db, "ticket_actual", str(nuevo_numero))
    return f"{prefijo}-{nuevo_numero:06d}"


# ============================================================
# MAESTROS
# ============================================================
def buscar_vehiculo_por_placa(placa: str) -> Optional[Vehiculo]:
    db = SessionLocal()
    try:
        return db.query(Vehiculo).filter(
            Vehiculo.placa == placa.strip().upper(),
            Vehiculo.activo == True
        ).first()
    finally:
        db.close()


def listar_vehiculos_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Vehiculo).filter_by(activo=True).order_by(Vehiculo.placa).all()
    finally:
        db.close()


def listar_conductores_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Conductor).filter_by(activo=True).order_by(Conductor.nombre).all()
    finally:
        db.close()


def listar_productos_activos() -> list:
    """Lista todos los productos activos (para kardex y reportes)."""
    db = SessionLocal()
    try:
        return db.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
    finally:
        db.close()


def listar_productos_por_tipo(tipo_pesaje: str) -> list:
    """
    Lista productos filtrados por tipo de pesaje.
    tipo_pesaje: "GENERAL" o "PRODUCTO_TERMINADO"
    """
    db = SessionLocal()
    try:
        return db.query(Producto).filter_by(
            activo=True,
            tipo_pesaje=tipo_pesaje
        ).order_by(Producto.codigo).all()
    finally:
        db.close()


def listar_proveedores_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Proveedor).filter_by(activo=True).order_by(Proveedor.nombre).all()
    finally:
        db.close()


def listar_destinos_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Destino).filter_by(activo=True).order_by(Destino.nombre).all()
    finally:
        db.close()


def listar_lotes_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Lote).filter_by(activo=True).order_by(Lote.codigo).all()
    finally:
        db.close()


def listar_remolques_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Remolque).filter_by(activo=True).order_by(Remolque.placa).all()
    finally:
        db.close()


def listar_contenedores_activos() -> list:
    db = SessionLocal()
    try:
        return db.query(Contenedor).filter_by(activo=True).order_by(Contenedor.codigo).all()
    finally:
        db.close()


# ============================================================
# CONSULTAS DE ESTADO
# ============================================================
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


def listar_pesadas_pendientes() -> list:
    """Compatibilidad con código anterior — alias de listar_pesadas_en_planta."""
    return listar_pesadas_en_planta()


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


def get_pesada_pendiente_por_vehiculo(vehiculo_id: int) -> Optional[Pesada]:
    """Alias para compatibilidad."""
    return get_pesada_en_planta_por_vehiculo(vehiculo_id)


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
    destino_id: Optional[int] = None,
    lote_id: Optional[int] = None,
    remolque_id: Optional[int] = None,
    contenedor_id: Optional[int] = None,
    observaciones: str = "",
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
        if peso_bruto < 200:
            return {"exito": False, "mensaje": "Peso muy bajo para un camión. Verifique la báscula"}

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

        numero_ticket = generar_numero_ticket(db)

        nueva_pesada = Pesada(
            numero_ticket=numero_ticket,
            estado="en_planta",
            tipo_pesaje=tipo_pesaje,
            fecha_entrada=datetime.now(),
            peso_bruto=round(float(peso_bruto), 2),
            vehiculo_id=vehiculo_id,
            conductor_id=conductor_id,
            cedula_conductor_libre=cedula_conductor_libre.strip() if cedula_conductor_libre else None,
            producto_id=producto_id,
            proveedor_id=proveedor_id,
            destino_id=destino_id,
            lote_id=lote_id,
            remolque_id=remolque_id,
            contenedor_id=contenedor_id,
            empresa_transportista=empresa_transportista.strip() if empresa_transportista else None,
            empresa_cliente_proveedor=empresa_cliente_proveedor.strip() if empresa_cliente_proveedor else None,
            usuario_entrada_id=_resolver_usuario_id(usuario_id),
            observaciones=observaciones
        )

        db.add(nueva_pesada)
        try:
            db.commit()
        except IntegrityError:
            # Red de seguridad ante condiciones de carrera: el chequeo de
            # "activa" de arriba es check-then-act y dos requests
            # concurrentes para el mismo vehículo podrían pasarlo ambas.
            # El índice único parcial ux_pesada_activa_por_vehiculo (ver
            # migración Alembic) es quien realmente lo impide a nivel BD.
            db.rollback()
            return {
                "exito": False,
                "mensaje": "El vehículo ya tiene una pesada activa (detectado por la base de datos). Intente de nuevo."
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

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error al registrar entrada: {str(e)}"}
    finally:
        db.close()


# ============================================================
# PASO 2: CAPTURAR PESO DE SALIDA → va a Centro de Costos
# ============================================================
def capturar_peso_salida(pesada_id: int, peso_capturado: float, usuario_id: Optional[int] = None) -> dict:
    """
    PASO 2: El camión volvió cargado, se captura el 2° peso.
    Se envía a la cola de Centro de Costos para aprobación.
    Estado resultante: "pendiente_aprobacion"
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

        # Calcular neto preliminar (bruto mayor, tara menor)
        peso1 = float(pesada.peso_bruto)
        peso2 = float(peso_capturado)

        if peso2 > peso1:
            bruto_real = peso2
            tara_real = peso1
        else:
            bruto_real = peso1
            tara_real = peso2

        neto = round(bruto_real - tara_real, 2)

        pesada.peso_tara = round(tara_real, 2)
        pesada.peso_bruto = round(bruto_real, 2)
        pesada.peso_neto = neto
        pesada.fecha_captura = datetime.now()
        pesada.estado = "pendiente_aprobacion"
        pesada.motivo_rechazo = None  # Limpiar rechazo anterior si hubo
        pesada.usuario_salida_id = _resolver_usuario_id(usuario_id)

        db.commit()
        pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=pesada.id).first()

        return {
            "exito": True,
            "mensaje": f"Peso capturado. Neto: {neto:,.0f} KG. Enviado a Centro de Costos.",
            "pesada": pesada,
            "peso_neto": neto
        }

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error al capturar peso: {str(e)}"}
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
        pesada.aprobado_por_id = _resolver_usuario_id(usuario_id)
        pesada.fecha_aprobacion = datetime.now()

        db.commit()
        pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=pesada.id).first()

        return {
            "exito": True,
            "mensaje": f"Pesada {pesada.numero_ticket} aprobada.",
            "pesada": pesada
        }

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error al aprobar: {str(e)}"}
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
        pesada.aprobado_por_id = _resolver_usuario_id(usuario_id)
        pesada.fecha_aprobacion = datetime.now()

        db.commit()

        return {
            "exito": True,
            "mensaje": f"Pesada {pesada.numero_ticket} rechazada. Romana debe volver a capturar.",
        }

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error al rechazar: {str(e)}"}
    finally:
        db.close()


# ============================================================
# PASO 4: COMPLETAR PESAJE (Romana, post-aprobación)
# ============================================================
def completar_pesaje(
    pesada_id: int,
    orden_compra: str = "",
    cantidad: Optional[float] = None,
    precintos: str = "",
    observaciones: str = "",
    usuario_id: Optional[int] = None
) -> dict:
    """
    PASO 4: Romana llena los datos finales y cierra la operación.
    Solo disponible después de que CC haya aprobado.
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

        pesada.orden_compra = orden_compra.strip() if orden_compra else None
        pesada.cantidad = round(float(cantidad), 2) if cantidad else None
        pesada.precintos = precintos.strip() if precintos else None
        pesada.observaciones = observaciones.strip() if observaciones else None
        pesada.estado = "completado"
        pesada.fecha_salida = datetime.now()
        pesada.usuario_salida_id = _resolver_usuario_id(usuario_id)

        db.commit()
        pesada = db.query(Pesada).options(*_pesada_options()).filter_by(
            id=pesada.id).first()

        return {
            "exito": True,
            "mensaje": f"Pesada {pesada.numero_ticket} completada. Neto: {float(pesada.peso_neto):,.0f} KG",
            "pesada": pesada
        }

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error al completar: {str(e)}"}
    finally:
        db.close()


# ============================================================
# ANULACIÓN
# ============================================================
def anular_pesada(pesada_id: int, motivo: str) -> dict:
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
        db.commit()

        return {"exito": True, "mensaje": f"Pesada {pesada.numero_ticket} anulada"}
    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error: {str(e)}"}
    finally:
        db.close()


# ============================================================
# CORTE
# ============================================================
def realizar_corte(observaciones: str = "", usuario_id: Optional[int] = None) -> dict:
    from database.models import Corte
    db = SessionLocal()
    try:
        ultimo_corte = db.query(Corte).order_by(Corte.id.desc()).first()
        fecha_inicio = ultimo_corte.fecha_fin if ultimo_corte else datetime(2000, 1, 1)
        fecha_fin = datetime.now()

        pesadas = db.query(Pesada).filter(
            Pesada.estado == "completado",
            Pesada.anulada == False,
            Pesada.fecha_salida >= fecha_inicio,
            Pesada.fecha_salida <= fecha_fin
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
            usuario_id=_resolver_usuario_id(usuario_id) or 1,
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

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error al realizar corte: {str(e)}"}
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


# ============================================================
# COMPATIBILIDAD REGISTRAR SALIDA (alias simplificado)
# ============================================================
def registrar_salida(pesada_id: int, peso_tara: float, observaciones: str = "") -> dict:
    """Alias de capturar_peso_salida para compatibilidad con código anterior."""
    return capturar_peso_salida(pesada_id, peso_tara)
