# ============================================================
# test_login_seguridad.py — I-09: enumeración, fuerza bruta, password corta
# ============================================================
# Antes: "Usuario no encontrado" vs "Contraseña incorrecta" permitía
# enumerar usuarios válidos; no había límite de intentos fallidos; se
# aceptaba una contraseña de un solo carácter al crear/cambiar usuario.


def test_login_mensaje_unificado_no_distingue_usuario_de_password(client, headers_romana):
    r_inexistente = client.post(
        "/api/v1/auth/login",
        json={"username": "usuario-que-no-existe-xyz", "password": "cualquiera123"},
    )
    r_password_mal = client.post(
        "/api/v1/auth/login",
        json={"username": "romana_test", "password": "password-incorrecta-xyz"},
    )
    assert r_inexistente.status_code == 401
    assert r_password_mal.status_code == 401
    assert r_inexistente.json()["detail"] == r_password_mal.json()["detail"]
    assert r_inexistente.json()["detail"] == "Usuario o contraseña incorrectos"


def test_login_bloquea_tras_varios_intentos_fallidos(client):
    username = "usuario-dedicado-test-bloqueo-i09"

    for _ in range(5):
        r = client.post("/api/v1/auth/login", json={"username": username, "password": "mal"})
        assert r.status_code == 401
        assert "intentos fallidos" not in r.json()["detail"].lower()

    # El intento número 6 debe quedar bloqueado por un rato, en vez de
    # seguir probando contraseñas indefinidamente.
    r = client.post("/api/v1/auth/login", json={"username": username, "password": "mal"})
    assert r.status_code == 401
    assert "intentos fallidos" in r.json()["detail"].lower()


def test_crear_usuario_rechaza_password_corta(client, headers_admin):
    r = client.post(
        "/api/v1/usuarios",
        json={"username": "test-pw-corta", "password": "123", "nombre_completo": "Test", "nivel": 3},
        headers=headers_admin,
    )
    assert r.status_code == 422  # error de validación de Pydantic, ni siquiera llega al servicio


def test_crear_usuario_acepta_password_de_longitud_valida(client, headers_admin):
    r = client.post(
        "/api/v1/usuarios",
        json={"username": "test-pw-valida", "password": "123456", "nombre_completo": "Test", "nivel": 3},
        headers=headers_admin,
    )
    assert r.status_code == 200, r.text
