# ============================================================
# test_run_server_seguridad.py — I-08 completo: fail-fast real
# ============================================================
# Antes solo advertía en consola; ahora aborta el arranque si el
# backend escucharía en una IP no local con el secreto JWT de
# desarrollo -- ver run_server.py.

import pytest

import run_server


def test_falla_si_secreto_default_y_host_no_local(monkeypatch):
    monkeypatch.setattr(run_server, "JWT_SECRET_KEY", run_server._JWT_SECRET_DEV)
    monkeypatch.setattr(run_server, "API_HOST", "0.0.0.0")
    with pytest.raises(SystemExit):
        run_server._fallar_si_secreto_por_defecto()


def test_no_falla_si_api_host_es_local(monkeypatch):
    monkeypatch.setattr(run_server, "JWT_SECRET_KEY", run_server._JWT_SECRET_DEV)
    monkeypatch.setattr(run_server, "API_HOST", "127.0.0.1")
    run_server._fallar_si_secreto_por_defecto()  # no debe lanzar


def test_no_falla_si_el_secreto_no_es_el_de_desarrollo(monkeypatch):
    monkeypatch.setattr(run_server, "JWT_SECRET_KEY", "un-secreto-propio-cualquiera")
    monkeypatch.setattr(run_server, "API_HOST", "0.0.0.0")
    run_server._fallar_si_secreto_por_defecto()  # no debe lanzar
