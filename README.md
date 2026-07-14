# Romana

Sistema de control de pesaje de camiones para Sura de Venezuela, C.A. (Planta Guacara). Cubre el flujo completo: ingreso y Tara, carga, retorno y Peso Bruto, calculo automatico de Peso Neto, aprobacion digital por Centro de Costos y cierre/facturacion -- reemplazando el software comercial rigido (Bigsoft) que se usaba antes.

## Arquitectura

Cliente-servidor: un backend HTTP + WebSocket centralizado (FastAPI) al que le apuntan dos GUIs de escritorio (customtkinter) -- la estacion de **Romana** (bascula) y la estacion de **Centro de Costos** (aprobaciones) -- cada una en su propia maquina fisica de la red de la planta.

```
backend/     API REST + WebSocket (FastAPI) -- autoridad real de datos y permisos
client/      Cliente HTTP/WS que usa la GUI para hablar con el backend
gui/         Interfaz de escritorio (customtkinter) -- Romana y Centro de Costos
services/    Logica de negocio y reglas de dominio (reusada por backend/)
database/    Modelos SQLAlchemy + migraciones Alembic
hardware/    Integracion con bascula Toledo (puerto serie) + simulador -- local a la estacion Romana
reports/     Plantillas y salida de tickets/reportes
```

El modelo de datos central es `Pesada`, con una maquina de estados explicita:
`en_planta -> pendiente_aprobacion -> aprobado/rechazado -> completado` (+ `anulado`). Los pesajes en estado `completado` son inmutables -- ni siquiera se pueden anular.

## Requisitos

- Python 3.11+ (probado con 3.14)
- PostgreSQL (configurar `DATABASE_URL` en `config.py`, o exportar `ROMANA_DATABASE_URL`)

```bash
pip install -r requirements.txt
```

## Arranque

Este sistema corre en **dos procesos separados**, tipicamente en dos maquinas distintas. Para pruebas en una sola maquina (por ejemplo, antes de instalar en la planta), no hace falta levantar los dos a mano: si `API_BASE_URL` apunta a `localhost` y el backend no esta corriendo, `python main.py` lo arranca solo como subproceso (y lo cierra al cerrar la GUI). En las estaciones reales de la red (`ROMANA_API_URL` apuntando a otra maquina) este auto-arranque no aplica -- ahi el backend se levanta aparte, en la maquina "servidor", con el paso 1 de abajo.

**1. Backend (una sola vez, en la maquina "servidor" de la red interna):**

```bash
python run_server.py
```

Corre con un unico worker de uvicorn -- el broadcast de WebSocket vive en memoria de un solo proceso; escalar a multiples workers requeriria un pub/sub externo (Redis), fuera del alcance actual.

Antes del primer arranque en una base de datos nueva, aplicar las migraciones:

```bash
alembic upgrade head
```

Si la base de datos ya existia de antes de introducir Alembic (con las tablas ya creadas por `database/seed.py`), marcar el baseline sin ejecutarlo:

```bash
alembic stamp head
```

En una base de datos nueva, sembrar los datos iniciales (usuarios por defecto, configuracion, catalogo de ejemplo) una sola vez:

```bash
python -m database.seed
```

`run_server.py` crea las tablas si no existen al arrancar, pero no siembra datos -- eso queda a criterio de quien despliega (no tiene sentido crear usuarios por defecto en cada arranque de un servidor de produccion).

**2. GUI (en cada estacion fisica -- Romana y Centro de Costos):**

```bash
python main.py
```

Cada estacion necesita ver al backend por red (`API_BASE_URL` en `config.py`, o `ROMANA_API_URL`). El display de bascula (puerto serie) es local a la estacion Romana -- no pasa por el backend, solo el peso final capturado.

## Tests

```bash
pytest backend/tests/
```

Corre contra un SQLite de archivo aislado (no requiere Postgres levantado) -- ver `backend/tests/conftest.py`.
