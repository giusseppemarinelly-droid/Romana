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

        # Shim de compatibilidad: la GUI aún no migrada (sidebar, header,
        # tiene_permiso(), etc.) sigue leyendo el usuario logueado desde
        # el global de services.auth_service. Se elimina en la fase de
        # limpieza final, cuando toda la GUI use exclusivamente este
        # cliente HTTP.
        from services.auth_service import _establecer_usuario_actual
        _establecer_usuario_actual(data["usuario"]["id"])

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
    def listar_pendientes_aprobacion(self) -> list:
        return self.get("/api/v1/pesadas/pendientes-aprobacion")

    def obtener_pesada(self, pesada_id: int) -> dict:
        return self.get(f"/api/v1/pesadas/{pesada_id}")

    def aprobar_pesada(self, pesada_id: int) -> dict:
        return self._con_pesada(self.post(f"/api/v1/pesadas/{pesada_id}/aprobar"))

    def rechazar_pesada(self, pesada_id: int, motivo: str) -> dict:
        return self._con_pesada(self.post(f"/api/v1/pesadas/{pesada_id}/rechazar", json={"motivo": motivo}))

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


class ApiError(Exception):
    """Error de un GET al backend (fallo de red o respuesta 4xx/5xx)."""
    pass


# Instancia única compartida por toda la GUI, igual que antes lo era
# el global de services.auth_service.
api_client = ApiClient()
