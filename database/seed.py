# ============================================================
# database/seed.py — Datos iniciales del sistema
# ============================================================

import bcrypt
from datetime import datetime
from database.engine import SessionLocal, crear_tablas
from database.models import (
    Usuario, Vehiculo, Conductor, Proveedor,
    Producto, Destino, Configuracion
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def crear_configuracion_inicial(db):
    """Crea los parámetros de configuración por defecto."""
    params = [
        ("nombre_empresa",   "MI EMPRESA, C.A.",      "Nombre de la empresa"),
        ("rif_empresa",      "J-000000000-0",          "RIF de la empresa"),
        ("direccion_empresa","Ciudad, Estado, País",   "Dirección de la empresa"),
        ("telefono_empresa", "+58 000-000-0000",       "Teléfono de la empresa"),
        ("ticket_actual",    "0",                      "Número del último ticket generado"),
        ("corte_actual",     "0",                      "Número del último corte realizado"),
        ("prefijo_ticket",   "TK",                     "Prefijo para número de ticket"),
        ("unidad_peso",      "KG",                     "Unidad de peso del sistema"),
        ("capacidad_max",    "80000",                  "Capacidad máxima de la báscula en KG"),
        ("puerto_com",       "COM1",                   "Puerto COM del display de pesaje"),
        ("baudrate",         "9600",                   "Velocidad del puerto COM"),
    ]
    for clave, valor, desc in params:
        existe = db.query(Configuracion).filter_by(clave=clave).first()
        if not existe:
            db.add(Configuracion(clave=clave, valor=valor, descripcion=desc))
    db.commit()
    print("OK - Configuracion inicial creada")


def crear_usuarios_iniciales(db):
    """Crea los usuarios predeterminados del sistema."""
    usuarios = [
        {
            "username":        "admin",
            "password":        "admin123",
            "nombre_completo": "Administrador del Sistema",
            "nivel":           1,
        },
        {
            "username":        "supervisor",
            "password":        "super123",
            "nombre_completo": "Supervisor de Planta",
            "nivel":           2,
        },
        {
            "username":        "operador",
            "password":        "oper123",
            "nombre_completo": "Operador de Báscula",
            "nivel":           3,
        },
        {
            "username":        "centrocostos",
            "password":        "cc123",
            "nombre_completo": "Analista Centro de Costos",
            "nivel":           4,  # Centro de Costos
        },
    ]

    for u in usuarios:
        existe = db.query(Usuario).filter_by(username=u["username"]).first()
        if not existe:
            db.add(Usuario(
                username=u["username"],
                password_hash=hash_password(u["password"]),
                nombre_completo=u["nombre_completo"],
                nivel=u["nivel"],
                activo=True,
                created_at=datetime.now()
            ))

    db.commit()
    print("OK - Usuarios iniciales creados")
    print("   admin / admin123          (Administrador)")
    print("   supervisor / super123     (Supervisor)")
    print("   operador / oper123        (Operador Romana)")
    print("   centrocostos / cc123      (Centro de Costos)")



def crear_productos_cliente(db):
    """
    Crea los productos específicos del cliente (Sura de Venezuela).
    Pesaje General + Producto Terminado.
    """
    productos = [
        # --- Pesaje General ---
        {"codigo": "002", "nombre": "Plásticos Reciclables",           "tipo_pesaje": "GENERAL"},
        {"codigo": "003", "nombre": "Cartones Reciclables",            "tipo_pesaje": "GENERAL"},
        {"codigo": "004", "nombre": "Archivo",                         "tipo_pesaje": "GENERAL"},
        {"codigo": "005", "nombre": "Chatarra",                        "tipo_pesaje": "GENERAL"},
        {"codigo": "006", "nombre": "Destruc. Productos No Conformes", "tipo_pesaje": "GENERAL"},
        # --- Producto Terminado ---
        {"codigo": "001", "nombre": "Despacho Producto Terminado",     "tipo_pesaje": "PRODUCTO_TERMINADO"},
    ]

    for p in productos:
        if not db.query(Producto).filter_by(codigo=p["codigo"]).first():
            db.add(Producto(
                codigo=p["codigo"],
                nombre=p["nombre"],
                unidad="KG",
                tipo_pesaje=p["tipo_pesaje"],
                activo=True,
                created_at=datetime.now()
            ))

    db.commit()
    print("OK - Productos del cliente creados (Pesaje General + Producto Terminado)")



def crear_datos_ejemplo(db):
    """Datos de ejemplo: proveedor, vehículo, conductor, destino."""
    # --- Proveedor ---
    prov = db.query(Proveedor).filter_by(codigo="PROV001").first()
    if not prov:
        prov = Proveedor(
            codigo="PROV001",
            nombre="Empresa Ejemplo, C.A.",
            rif="J-12345678-9",
            direccion="Av. Principal, Zona Industrial",
            telefono="0212-555-0100",
            email="info@ejemplo.com"
        )
        db.add(prov)
        db.flush()

    # --- Vehículo ---
    if not db.query(Vehiculo).filter_by(placa="ABC-123").first():
        db.add(Vehiculo(
            placa="ABC-123",
            descripcion="Mack CH613 Rojo - 2018",
            tara_registrada=12500,
            tipo="camion",
            proveedor_id=prov.id
        ))

    # --- Conductor ---
    if not db.query(Conductor).filter_by(documento="V-12345678").first():
        db.add(Conductor(
            nombre="Juan Pérez García",
            documento="V-12345678",
            tipo_documento="cedula",
            telefono="0414-555-0200"
        ))

    # --- Destino ---
    if not db.query(Destino).filter_by(codigo="DEST001").first():
        db.add(Destino(
            codigo="DEST001",
            nombre="Almacén Principal",
            descripcion="Almacén central de la planta"
        ))

    db.commit()
    print("OK - Datos de ejemplo creados")


def inicializar_base_de_datos():
    print("\nInicializando Sistema de Romana para Camiones...")
    print("=" * 50)

    crear_tablas()

    db = SessionLocal()
    try:
        crear_configuracion_inicial(db)
        crear_usuarios_iniciales(db)
        crear_productos_cliente(db)
        crear_datos_ejemplo(db)
        print("=" * 50)
        print("OK - Sistema listo para usar")
        print("=" * 50)
    except Exception as e:
        db.rollback()
        print(f"ERROR al inicializar: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    inicializar_base_de_datos()
