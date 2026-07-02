# ============================================================
# database/models.py — Modelos (tablas) de la base de datos
# ============================================================

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Numeric, Text, ForeignKey, Index, text
)
from sqlalchemy.orm import relationship
from database.engine import Base

_CONDICION_PESADA_ACTIVA = (
    "estado IN ('en_planta','pendiente_aprobacion','aprobado','rechazado') AND anulada = false"
)


# ============================================================
# TABLA: usuarios
# ============================================================
class Usuario(Base):
    """
    Almacena los usuarios del sistema con sus credenciales y nivel de acceso.
    Nivel 1 = Administrador      (acceso total)
    Nivel 2 = Supervisor         (sin gestión de usuarios)
    Nivel 3 = Operador Romana    (solo pesajes)
    Nivel 4 = Centro de Costos   (solo aprobaciones)
    """
    __tablename__ = "usuarios"

    id             = Column(Integer, primary_key=True, index=True)
    username       = Column(String(50),  unique=True, nullable=False)
    password_hash  = Column(String(255), nullable=False)
    nombre_completo= Column(String(100), nullable=False)
    nivel          = Column(Integer, default=3)          # 1, 2, 3 o 4
    activo         = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.now)
    last_login     = Column(DateTime, nullable=True)

    # Relaciones
    pesadas_entrada  = relationship("Pesada", foreign_keys="Pesada.usuario_entrada_id",
                                    back_populates="usuario_entrada")
    pesadas_salida   = relationship("Pesada", foreign_keys="Pesada.usuario_salida_id",
                                    back_populates="usuario_salida")
    pesadas_aprobadas= relationship("Pesada", foreign_keys="Pesada.aprobado_por_id",
                                    back_populates="aprobado_por")
    cortes           = relationship("Corte", back_populates="usuario")

    def __repr__(self):
        return f"<Usuario {self.username} (nivel={self.nivel})>"


# ============================================================
# TABLA: vehiculos
# ============================================================
class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id               = Column(Integer, primary_key=True, index=True)
    placa            = Column(String(20), unique=True, nullable=False)
    descripcion      = Column(String(100))
    tara_registrada  = Column(Numeric(10, 2), default=0)
    tipo             = Column(String(30), default="camion")
    proveedor_id     = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    activo           = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.now)

    proveedor        = relationship("Proveedor", back_populates="vehiculos")
    pesadas          = relationship("Pesada", back_populates="vehiculo")

    def __repr__(self):
        return f"<Vehiculo {self.placa}>"


# ============================================================
# TABLA: conductores
# ============================================================
class Conductor(Base):
    __tablename__ = "conductores"

    id             = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String(100), nullable=False)
    documento      = Column(String(30), unique=True, nullable=False)
    tipo_documento = Column(String(20), default="cedula")
    telefono       = Column(String(20), nullable=True)
    activo         = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.now)

    pesadas        = relationship("Pesada", back_populates="conductor")

    def __repr__(self):
        return f"<Conductor {self.nombre} - {self.documento}>"


# ============================================================
# TABLA: proveedores
# ============================================================
class Proveedor(Base):
    __tablename__ = "proveedores"

    id         = Column(Integer, primary_key=True, index=True)
    codigo     = Column(String(20), unique=True, nullable=False)
    nombre     = Column(String(100), nullable=False)
    rif        = Column(String(20), nullable=True)
    direccion  = Column(Text, nullable=True)
    telefono   = Column(String(20), nullable=True)
    email      = Column(String(100), nullable=True)
    activo     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    vehiculos  = relationship("Vehiculo", back_populates="proveedor")
    pesadas    = relationship("Pesada", back_populates="proveedor")
    lotes      = relationship("Lote", back_populates="proveedor")

    def __repr__(self):
        return f"<Proveedor {self.codigo} - {self.nombre}>"


# ============================================================
# TABLA: productos
# ============================================================
class Producto(Base):
    """
    Materiales que se pesan.
    tipo_pesaje indica en qué tipo de pesaje aparece este producto:
      "GENERAL"           → solo en Pesaje General
      "PRODUCTO_TERMINADO"→ solo en Producto Terminado
    """
    __tablename__ = "productos"

    id          = Column(Integer, primary_key=True, index=True)
    codigo      = Column(String(20), unique=True, nullable=False)
    nombre      = Column(String(100), nullable=False)
    unidad      = Column(String(10), default="KG")
    tipo_pesaje = Column(String(30), default="GENERAL")  # GENERAL / PRODUCTO_TERMINADO
    descripcion = Column(Text, nullable=True)
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)

    lotes       = relationship("Lote", back_populates="producto")
    pesadas     = relationship("Pesada", back_populates="producto")

    def __repr__(self):
        return f"<Producto {self.codigo} - {self.nombre}>"


# ============================================================
# TABLA: lotes
# ============================================================
class Lote(Base):
    __tablename__ = "lotes"

    id          = Column(Integer, primary_key=True, index=True)
    codigo      = Column(String(50), unique=True, nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    proveedor_id= Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    descripcion = Column(Text, nullable=True)
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)

    producto    = relationship("Producto", back_populates="lotes")
    proveedor   = relationship("Proveedor", back_populates="lotes")
    pesadas     = relationship("Pesada", back_populates="lote")

    def __repr__(self):
        return f"<Lote {self.codigo}>"


# ============================================================
# TABLA: destinos
# ============================================================
class Destino(Base):
    __tablename__ = "destinos"

    id          = Column(Integer, primary_key=True, index=True)
    codigo      = Column(String(20), unique=True, nullable=False)
    nombre      = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)

    pesadas     = relationship("Pesada", back_populates="destino")

    def __repr__(self):
        return f"<Destino {self.codigo} - {self.nombre}>"


# ============================================================
# TABLA: remolques
# ============================================================
class Remolque(Base):
    __tablename__ = "remolques"

    id               = Column(Integer, primary_key=True, index=True)
    placa            = Column(String(20), unique=True, nullable=False)
    descripcion      = Column(String(100), nullable=True)
    tara_registrada  = Column(Numeric(10, 2), default=0)
    activo           = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.now)

    pesadas          = relationship("Pesada", back_populates="remolque")

    def __repr__(self):
        return f"<Remolque {self.placa}>"


# ============================================================
# TABLA: contenedores
# ============================================================
class Contenedor(Base):
    __tablename__ = "contenedores"

    id          = Column(Integer, primary_key=True, index=True)
    codigo      = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(100), nullable=True)
    tara        = Column(Numeric(10, 2), default=0)
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.now)

    pesadas     = relationship("Pesada", back_populates="contenedor")

    def __repr__(self):
        return f"<Contenedor {self.codigo}>"


# ============================================================
# TABLA: pesadas  ← TABLA PRINCIPAL DEL SISTEMA
# ============================================================
class Pesada(Base):
    """
    Registro de cada operación de pesaje.

    FLUJO DE ESTADOS:
      "en_planta"            → Camión entró, fue pesado (peso entrada), esperando ser cargado
      "pendiente_aprobacion" → 2° peso capturado por Romana, esperando aprobación de CC
      "aprobado"             → Centro de Costos aprobó, Romana puede completar datos
      "rechazado"            → Centro de Costos rechazó, vuelve a capturar peso
      "completado"           → Datos finales llenados, proceso cerrado
      "anulado"              → Cancelado por cualquier motivo
    """
    __tablename__ = "pesadas"
    __table_args__ = (
        # Un vehículo no puede tener 2 pesadas activas a la vez. Se
        # declara acá (no solo como chequeo en pesaje_service.py) para
        # que la propia base de datos cierre la condición de carrera
        # bajo escrituras concurrentes — ver también la migración
        # Alembic ux_pesada_activa_por_vehiculo, que aplica lo mismo
        # sobre una BD ya existente.
        Index(
            "ux_pesada_activa_por_vehiculo",
            "vehiculo_id",
            unique=True,
            postgresql_where=text(_CONDICION_PESADA_ACTIVA),
            sqlite_where=text(_CONDICION_PESADA_ACTIVA),
        ),
    )

    id                       = Column(Integer, primary_key=True, index=True)
    numero_ticket            = Column(String(20), unique=True, nullable=False)
    estado                   = Column(String(30), default="en_planta")

    # --- Tipo de pesaje ---
    tipo_pesaje              = Column(String(30), default="GENERAL")
                                     # "GENERAL" o "PRODUCTO_TERMINADO"

    # --- Timestamps ---
    fecha_entrada            = Column(DateTime, nullable=True)
    fecha_captura            = Column(DateTime, nullable=True)   # 2° peso capturado
    fecha_aprobacion         = Column(DateTime, nullable=True)
    fecha_salida             = Column(DateTime, nullable=True)   # Fecha de completado

    # --- Pesos (KG) ---
    peso_bruto               = Column(Numeric(10, 2), nullable=True)  # Peso entrada
    peso_tara                = Column(Numeric(10, 2), nullable=True)  # Peso salida (2°)
    peso_neto                = Column(Numeric(10, 2), nullable=True)  # Calculado

    # --- Datos de la empresa (texto libre, no FK) ---
    empresa_transportista    = Column(String(150), nullable=True)
    empresa_cliente_proveedor= Column(String(150), nullable=True)
    cedula_conductor_libre   = Column(String(30), nullable=True)  # Si no está en maestros

    # --- Datos post-aprobación (llena Romana después de que CC aprueba) ---
    orden_compra             = Column(String(100), nullable=True)
    cantidad                 = Column(Numeric(10, 2), nullable=True)
    precintos                = Column(String(200), nullable=True)
    observaciones            = Column(Text, nullable=True)
    motivo_rechazo           = Column(Text, nullable=True)

    # --- Relaciones con maestros ---
    vehiculo_id              = Column(Integer, ForeignKey("vehiculos.id"),    nullable=False)
    conductor_id             = Column(Integer, ForeignKey("conductores.id"),  nullable=True)
    producto_id              = Column(Integer, ForeignKey("productos.id"),    nullable=True)
    proveedor_id             = Column(Integer, ForeignKey("proveedores.id"),  nullable=True)
    destino_id               = Column(Integer, ForeignKey("destinos.id"),     nullable=True)
    lote_id                  = Column(Integer, ForeignKey("lotes.id"),        nullable=True)
    remolque_id              = Column(Integer, ForeignKey("remolques.id"),    nullable=True)
    contenedor_id            = Column(Integer, ForeignKey("contenedores.id"), nullable=True)

    # --- Usuarios ---
    usuario_entrada_id       = Column(Integer, ForeignKey("usuarios.id"),     nullable=True)
    usuario_salida_id        = Column(Integer, ForeignKey("usuarios.id"),     nullable=True)
    aprobado_por_id          = Column(Integer, ForeignKey("usuarios.id"),     nullable=True)

    # --- Control ---
    anulada                  = Column(Boolean, default=False)
    motivo_anulacion         = Column(Text, nullable=True)

    # --- Relaciones Python ---
    vehiculo        = relationship("Vehiculo",    back_populates="pesadas")
    conductor       = relationship("Conductor",   back_populates="pesadas")
    producto        = relationship("Producto",    back_populates="pesadas")
    proveedor       = relationship("Proveedor",   back_populates="pesadas")
    destino         = relationship("Destino",     back_populates="pesadas")
    lote            = relationship("Lote",        back_populates="pesadas")
    remolque        = relationship("Remolque",    back_populates="pesadas")
    contenedor      = relationship("Contenedor",  back_populates="pesadas")
    usuario_entrada = relationship("Usuario", foreign_keys=[usuario_entrada_id],
                                  back_populates="pesadas_entrada")
    usuario_salida  = relationship("Usuario", foreign_keys=[usuario_salida_id],
                                  back_populates="pesadas_salida")
    aprobado_por    = relationship("Usuario", foreign_keys=[aprobado_por_id],
                                  back_populates="pesadas_aprobadas")

    def __repr__(self):
        return f"<Pesada {self.numero_ticket} - {self.estado}>"


# ============================================================
# TABLA: cortes
# ============================================================
class Corte(Base):
    __tablename__ = "cortes"

    id              = Column(Integer, primary_key=True, index=True)
    numero_corte    = Column(Integer, unique=True, nullable=False)
    fecha_inicio    = Column(DateTime, nullable=False)
    fecha_fin       = Column(DateTime, nullable=False)
    total_pesadas   = Column(Integer, default=0)
    total_neto_kg   = Column(Numeric(12, 2), default=0)
    usuario_id      = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    observaciones   = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.now)

    usuario         = relationship("Usuario", back_populates="cortes")

    def __repr__(self):
        return f"<Corte #{self.numero_corte}>"


# ============================================================
# TABLA: configuracion
# ============================================================
class Configuracion(Base):
    __tablename__ = "configuracion"

    id          = Column(Integer, primary_key=True, index=True)
    clave       = Column(String(50), unique=True, nullable=False)
    valor       = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Config {self.clave}={self.valor}>"
