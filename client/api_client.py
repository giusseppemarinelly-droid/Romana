# ============================================================
# client/api_client.py — Cliente HTTP del backend (reemplaza el
# acceso directo a SQLAlchemy desde la GUI, vista por vista, a medida
# que avanza la migración a cliente-servidor)
# ============================================================
# Guarda el JWT en memoria de proceso (no hay nada persistente en
# disco) — cada vez que se abre la app hay que loguearse de nuevo,
# igual que antes. Los métodos de mutación (post/patch) devuelven un
# dict con la misma forma {"exito", "mensaje", ...} que ya devolvían
# las funciones de services/pesaje_service.py, para minimizar cambios
# en las vistas de gui/ que se van migrando.

from typing import Any, Optional

import httpx

from config import API_BASE_URL
from services.auth_service import PERMISOS


class ApiClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=10.0)
        self._token: Optional[str] = None
        self.usuario: Optional[dict] = None

    # ------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------
    def login(self, username: str, password: str) -> dict:
        try:
            r = self._client.post("/api/v1/auth/login", json={"username": username, "password": password})
        except httpx.RequestError as e:
            return {"exito": False, "mensaje": f"No se pudo conectar al servidor ({self._base_url}): {e}", "usuario": None}

        if r.status_code != 200:
            return {"exito": False, "mensaje": self._detalle(r), "usuario": None}

        data = r.json()
        self._token = data["access_token"]
        self.usuario = data["usuario"]

        return {
            "exito": True,
            "mensaje": f"Bienvenido, {data['usuario']['nombre_completo']}",
            "usuario": data["usuario"],
            "nivel_nombre": data["nivel_nombre"],
        }

    def logout(self):
        self._token = None
        self.usuario = None

    @property
    def autenticado(self) -> bool:
        return self._token is not None

    @property
    def token(self) -> Optional[str]:
        return self._token

    def get_nivel_actual(self) -> int:
        return self.usuario["nivel"] if self.usuario else 0

    def tiene_permiso(self, accion: str) -> bool:
        """
        Reemplaza a services.auth_service.tiene_permiso(): antes leía el
        nivel del usuario desde el global _usuario_actual, ahora lo lee
        del login de esta misma instancia de ApiClient. La autoridad real
        sigue siendo el backend (Depends(requiere_permiso(...)) en cada
        endpoint) — esto solo decide qué botones mostrar en la GUI.
        """
        if not self.usuario:
            return False
        return self.usuario["nivel"] in PERMISOS.get(accion, [])

    # ------------------------------------------------------------
    # Helpers HTTP genéricos
    # ------------------------------------------------------------
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def _detalle(self, r: httpx.Response) -> str:
        try:
            return r.json().get("detail", r.text)
        except Exception:
            return r.text or f"Error HTTP {r.status_code}"

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        """GET simple: devuelve el JSON parseado o lanza ApiError."""
        try:
            r = self._client.get(path, params=params, headers=self._headers())
        except httpx.RequestError as e:
            raise ApiError(f"No se pudo conectar al servidor: {e}")
        if r.status_code >= 400:
            raise ApiError(self._detalle(r))
        return r.json() if r.content else None

    def _mutar(self, metodo: str, path: str, json: Optional[dict] = None) -> dict:
        """POST/PUT/PATCH que devuelve {"exito", "mensaje", "data"} — el
        formato que ya esperaban las vistas migradas desde services/pesaje_service."""
        try:
            r = self._client.request(metodo, path, json=json if json is not None else {}, headers=self._headers())
        except httpx.RequestError as e:
            return {"exito": False, "mensaje": f"No se pudo conectar al servidor: {e}"}
        if r.status_code >= 400:
            return {"exito": False, "mensaje": self._detalle(r)}
        return {"exito": True, "mensaje": "", "data": r.json() if r.content else None}

    def post(self, path: str, json: Optional[dict] = None) -> dict:
        return self._mutar("POST", path, json)

    def put(self, path: str, json: Optional[dict] = None) -> dict:
        return self._mutar("PUT", path, json)

    def patch(self, path: str, json: Optional[dict] = None) -> dict:
        return self._mutar("PATCH", path, json)

    # ------------------------------------------------------------
    # Dominio: pesadas (mapea 1:1 backend/routers/pesadas.py)
    # ------------------------------------------------------------
    def listar_pesadas_en_planta(self) -> list:
        return self.get("/api/v1/pesadas/en-planta")

    def listar_pendientes_aprobacion(self) -> list:
        return self.get("/api/v1/pesadas/pendientes-aprobacion")

    def listar_aprobadas_pendientes(self) -> list:
        return self.get("/api/v1/pesadas/aprobadas-pendientes")

    def listar_pesadas_completadas(self, limit: int = 100) -> list:
        return self.get("/api/v1/pesadas/completadas", params={"limit": limit})

    def get_kardex(self, **params) -> list:
        return self.get("/api/v1/pesadas/kardex/buscar", params={k: v for k, v in params.items() if v is not None})

    def obtener_pesada(self, pesada_id: int) -> dict:
        return self.get(f"/api/v1/pesadas/{pesada_id}")

    def registrar_entrada(self, **kwargs) -> dict:
        resultado = self._con_pesada(self.post("/api/v1/pesadas/entrada", json=kwargs))
        if resultado["exito"]:
            resultado["ticket"] = resultado["pesada"]["numero_ticket"]
        return resultado

    def capturar_salida(self, pesada_id: int, peso_capturado: float) -> dict:
        resultado = self._con_pesada(self.post(f"/api/v1/pesadas/{pesada_id}/salida", json={"peso_capturado": peso_capturado}))
        if resultado["exito"]:
            resultado["peso_neto"] = resultado["pesada"]["peso_neto"]
        return resultado

    def aprobar_pesada(self, pesada_id: int) -> dict:
        return self._con_pesada(self.post(f"/api/v1/pesadas/{pesada_id}/aprobar"))

    def rechazar_pesada(self, pesada_id: int, motivo: str) -> dict:
        return self._con_pesada(self.post(f"/api/v1/pesadas/{pesada_id}/rechazar", json={"motivo": motivo}))

    def completar_pesaje(self, pesada_id: int, **kwargs) -> dict:
        return self._con_pesada(self.post(f"/api/v1/pesadas/{pesada_id}/completar", json=kwargs))

    def anular_pesada(self, pesada_id: int, motivo: str) -> dict:
        resultado = self.post(f"/api/v1/pesadas/{pesada_id}/anular", json={"motivo": motivo})
        if resultado["exito"]:
            resultado["mensaje"] = resultado.pop("data")["mensaje"]
        return resultado

    def listar_cortes(self, limit: int = 20) -> list:
        return self.get("/api/v1/pesadas/cortes", params={"limit": limit})

    def realizar_corte(self, observaciones: str = "") -> dict:
        resultado = self.post("/api/v1/pesadas/cortes", json={"observaciones": observaciones})
        if resultado["exito"]:
            corte = resultado.pop("data")
            resultado.update(corte)
            resultado["mensaje"] = f"Corte #{corte['numero_corte']} realizado"
        return resultado

    @staticmethod
    def _con_pesada(resultado: dict) -> dict:
        if resultado["exito"]:
            resultado["pesada"] = resultado.pop("data")
        return resultado

    # ------------------------------------------------------------
    # Dominio: maestros (mapea 1:1 backend/routers/maestros.py)
    # ------------------------------------------------------------
    # Un único conjunto de métodos genéricos para los 5 catálogos
    # (vehiculos, conductores, proveedores, productos, destinos) — el
    # backend ya los expone con la misma forma de endpoint
    # (crear_router_maestro), así que no hace falta repetir esto 5
    # veces en el cliente tampoco.
    def listar_maestro(self, recurso: str, search: Optional[str] = None, activo: Optional[bool] = True) -> list:
        params = {}
        if search:
            params["search"] = search
        if activo is not None:
            params["activo"] = activo
        return self.get(f"/api/v1/{recurso}", params=params)

    def obtener_maestro(self, recurso: str, item_id: int) -> dict:
        return self.get(f"/api/v1/{recurso}/{item_id}")

    def crear_maestro(self, recurso: str, datos: dict) -> dict:
        return self._mutar("POST", f"/api/v1/{recurso}", datos)

    def actualizar_maestro(self, recurso: str, item_id: int, datos: dict) -> dict:
        return self._mutar("PUT", f"/api/v1/{recurso}/{item_id}", datos)

    def desactivar_maestro(self, recurso: str, item_id: int, activo: bool = False) -> dict:
        return self._mutar("PATCH", f"/api/v1/{recurso}/{item_id}/activo", {"activo": activo})

    def autoregistrar_vehiculo(self, datos: dict) -> dict:
        """Registro rápido de un vehículo no catalogado al pesar — permiso
        'pesaje_entrada' (niveles 1-3), a diferencia de crear_maestro
        ('maestros_crear', solo 1-2)."""
        return self._mutar("POST", "/api/v1/vehiculos/autoregistro", datos)

    # ------------------------------------------------------------
    # Dominio: administración (mapea 1:1 backend/routers/admin.py)
    # ------------------------------------------------------------
    def listar_usuarios(self) -> list:
        return self.get("/api/v1/usuarios")

    def crear_usuario(self, username: str, password: str, nombre_completo: str, nivel: int) -> dict:
        return self._mutar("POST", "/api/v1/usuarios", {
            "username": username, "password": password,
            "nombre_completo": nombre_completo, "nivel": nivel,
        })

    def cambiar_password(self, usuario_id: int, nueva_password: str) -> dict:
        return self._mutar("POST", f"/api/v1/usuarios/{usuario_id}/password", {"nueva_password": nueva_password})

    def activar_desactivar_usuario(self, usuario_id: int, activo: bool) -> dict:
        return self._mutar("PATCH", f"/api/v1/usuarios/{usuario_id}/activo", {"activo": activo})

    def listar_configuracion(self) -> list:
        return self.get("/api/v1/configuracion")

    def actualizar_configuracion(self, clave: str, valor: str) -> dict:
        return self._mutar("PUT", f"/api/v1/configuracion/{clave}", {"valor": valor})

    # ------------------------------------------------------------
    # Dominio: reportes (mapea 1:1 backend/routers/reportes.py)
    # ------------------------------------------------------------
    # El PDF/Excel se genera en el servidor (Romana y Centro de Costos
    # no comparten disco) y se descarga como bytes — el llamador decide
    # dónde guardarlo localmente antes de abrirlo.
    def _descargar(self, path: str, params: Optional[dict] = None) -> bytes:
        try:
            r = self._client.get(path, params=params, headers=self._headers())
        except httpx.RequestError as e:
            raise ApiError(f"No se pudo conectar al servidor: {e}")
        if r.status_code >= 400:
            raise ApiError(self._detalle(r))
        return r.content

    def descargar_ticket_pdf(self, pesada_id: int) -> bytes:
        return self._descargar(f"/api/v1/reportes/ticket/{pesada_id}.pdf")

    def descargar_kardex_pdf(self, **filtros) -> bytes:
        return self._descargar("/api/v1/reportes/kardex.pdf", params={k: v for k, v in filtros.items() if v is not None})

    def descargar_kardex_excel(self, **filtros) -> bytes:
        return self._descargar("/api/v1/reportes/kardex.xlsx", params={k: v for k, v in filtros.items() if v is not None})


class ApiError(Exception):
    """Error de un GET al backend (fallo de red o respuesta 4xx/5xx)."""
    pass


# Instancia única compartida por toda la GUI, igual que antes lo era
# el global de services.auth_service.
api_client = ApiClient()
