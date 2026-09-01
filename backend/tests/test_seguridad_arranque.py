# ============================================================
# backend/tests/test_seguridad_arranque.py
# ============================================================
# El backend debe negarse a arrancar en una configuración que quede insegura
# en la red de la planta, en vez de levantar igual y no avisar nunca.
import importlib

import pytest


def _verificar_con(monkeypatch, secreto: str, host: str):
    """
    Recarga config y backend.security con el secreto dado -- ambos leen
    JWT_SECRET_KEY a nivel de módulo, así que no alcanza con tocar os.environ.
    """
    monkeypatch.setenv("ROMANA_JWT_SECRET", secreto)
    import config
    import backend.security as security

    importlib.reload(config)
    importlib.reload(security)
    try:
        security.verificar_secreto_de_produccion(host)
    finally:
        # Dejar los módulos como estaban para no contaminar los demás tests,
        # que comparten proceso y firman tokens con el secreto de conftest.
        monkeypatch.undo()
        importlib.reload(config)
        importlib.reload(security)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.50"])
def test_no_arranca_con_el_secreto_de_desarrollo_escuchando_en_la_red(monkeypatch, host):
    """
    El secreto por defecto está escrito en config.py y por lo tanto en el
    repositorio: cualquiera que lo lea puede firmarse un token de nivel 1.
    Atado a una interfaz de red, eso es acceso de Administrador para toda la
    planta.
    """
    with pytest.raises(RuntimeError, match="ROMANA_JWT_SECRET"):
        _verificar_con(monkeypatch, "dev-secret-cambiar-en-produccion", host)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_arranca_con_el_secreto_de_desarrollo_en_loopback(monkeypatch, host):
    """
    Atado a loopback el único cliente posible es la GUI de esta misma máquina,
    que es como main.py arranca el backend de desarrollo. Ese flujo tiene que
    seguir funcionando sin obligar a definir un secreto.
    """
    _verificar_con(monkeypatch, "dev-secret-cambiar-en-produccion", host)


def test_arranca_en_la_red_con_un_secreto_propio(monkeypatch):
    _verificar_con(monkeypatch, "un-secreto-real-generado-con-secrets", "0.0.0.0")
