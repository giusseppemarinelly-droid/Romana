# ============================================================
# Montaje de la web de supervisión (web/dist) en el backend
# ============================================================
# Deterministas a propósito: no dependen de si web/dist está compilado
# en la máquina que corre los tests -- usan un dist falso en tmp_path
# sobre una app FastAPI mínima. El único test sobre la app real
# (test_app_real_mantiene_el_405_de_la_api) pasa en los dos casos.
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.main import montar_web_supervision


def _dist_falso(tmp_path) -> str:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>web de supervision</h1>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return str(tmp_path)


def _app_con_una_ruta_de_api() -> FastAPI:
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    def login():
        return {"ok": True}

    return app


def test_sirve_la_web_bajo_supervision(tmp_path):
    app = _app_con_una_ruta_de_api()
    assert montar_web_supervision(app, _dist_falso(tmp_path)) is True
    c = TestClient(app)

    r = c.get("/supervision/")
    assert r.status_code == 200
    assert "web de supervision" in r.text
    assert c.get("/supervision/assets/app.js").status_code == 200


def test_la_raiz_y_supervision_sin_barra_redirigen_a_la_web(tmp_path):
    app = _app_con_una_ruta_de_api()
    montar_web_supervision(app, _dist_falso(tmp_path))
    c = TestClient(app)

    for ruta in ("/", "/supervision"):
        for metodo in ("GET", "HEAD"):
            r = c.request(metodo, ruta, follow_redirects=False)
            assert r.status_code == 307, (metodo, ruta)
            assert r.headers["location"].endswith("/supervision/"), (metodo, ruta)


def test_no_cambia_las_respuestas_de_error_de_la_api(tmp_path):
    # Montada en "/" (la receta típica de FastAPI) la web se quedaba con
    # los requests que ninguna ruta matcheaba del todo, y un método
    # equivocado pasaba de 405 a 404 -- comprobado con Starlette 0.41.
    app = _app_con_una_ruta_de_api()
    montar_web_supervision(app, _dist_falso(tmp_path))
    c = TestClient(app)

    r = c.get("/api/v1/auth/login")
    assert r.status_code == 405
    assert r.json() == {"detail": "Method Not Allowed"}

    r = c.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}


def test_sin_compilar_no_monta_nada_y_la_api_sigue_andando(tmp_path):
    for directorio in (tmp_path / "no-existe", tmp_path):  # inexistente / vacío (build a medias)
        app = _app_con_una_ruta_de_api()
        assert montar_web_supervision(app, str(directorio)) is False
        c = TestClient(app)

        assert c.get("/supervision/").status_code == 404
        assert c.get("/").status_code == 404
        assert c.post("/api/v1/auth/login").json() == {"ok": True}


def test_app_real_mantiene_el_405_de_la_api(client):
    r = client.get("/api/v1/auth/login")
    assert r.status_code == 405
    assert r.json() == {"detail": "Method Not Allowed"}
