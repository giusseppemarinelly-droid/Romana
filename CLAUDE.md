# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

Sistema de control de pesaje de camiones para Sura de Venezuela, C.A. (Planta Guacara). Cubre el flujo completo: ingreso y Tara, carga, retorno y Peso Bruto, cálculo automático de Peso Neto, aprobación digital por Centro de Costos y cierre/facturación — reemplaza el software comercial rígido (Bigsoft) que se usaba antes.

## Arquitectura

Cliente-servidor: un backend HTTP + WebSocket centralizado (FastAPI) al que le apuntan dos GUIs de escritorio (customtkinter) — la estación de **Romana** (báscula) y la estación de **Centro de Costos** (aprobaciones) — cada una en su propia máquina física de la red de la planta.

```
backend/     API REST + WebSocket (FastAPI) -- autoridad real de datos y permisos
client/      Cliente HTTP/WS que usa la GUI para hablar con el backend
gui/         Interfaz de escritorio (customtkinter) -- Romana y Centro de Costos
services/    Lógica de negocio y reglas de dominio (reusada por backend/)
database/    Modelos SQLAlchemy + migraciones Alembic
hardware/    Integración con báscula Toledo (puerto serie) + simulador -- local a la estación Romana
reports/     Plantillas y salida de tickets/reportes
```

Ninguna GUI toca Postgres directamente: hablan con `backend/` por HTTP (`client/api_client.py`) y WebSocket (`client/ws_client.py`). Solo `backend/main.py` (vía `run_server.py`) crea las tablas al arrancar.

### Máquina de estados de `Pesada`

El modelo central es `Pesada` (`database/models.py`), con estados explícitos:

```
en_planta -> pendiente_aprobacion -> aprobado/rechazado -> completado   (+ anulado)
```

- `en_planta`: camión entró, primer peso capturado, esperando ser cargado.
- `pendiente_aprobacion`: 2° peso capturado por Romana, esperando aprobación de Centro de Costos.
- `aprobado` / `rechazado`: decisión de Centro de Costos; si rechaza, vuelve a capturar peso.
- `completado`: datos finales llenados, proceso cerrado — **inmutable, ni siquiera se puede anular**.
- `anulado`: cancelado por cualquier motivo (excepto desde `completado`).

Un vehículo no puede tener 2 pesadas activas a la vez — se aplica con un índice único parcial de Postgres (`ux_pesada_activa_por_vehiculo` en `database/models.py` y la migración homónima), no solo con un chequeo en `services/pesaje_service.py`, para cerrar la condición de carrera bajo escrituras concurrentes.

### Backend (`backend/`)

- Un único worker de uvicorn (`workers=1` en `run_server.py`) — el broadcast de WebSocket (`backend/ws/manager.py`) vive en memoria de un solo proceso; escalar a múltiples workers requeriría un pub/sub externo (Redis), fuera del alcance actual.
- Auth: JWT en header `Authorization: Bearer` (`backend/security.py`), no cookies — los clientes son apps de escritorio, no hay navegador de por medio. `JWT_SECRET_KEY` debe venir de `ROMANA_JWT_SECRET` en producción.
- Permisos por nivel de usuario centralizados en `services/auth_service.PERMISOS` — es la única fuente de verdad, la reusan `backend/deps.requiere_permiso()` (autoridad real, servidor) y la GUI (para decidir qué mostrar). Niveles: 1=Administrador, 2=Supervisor, 3=Operador Romana, 4=Centro de Costos.
- CORS abierto (`allow_origins=["*"]`) intencional: no hay navegador de por medio, solo apps de escritorio en la red interna.
- WebSocket (`backend/ws/`) es notificación best-effort, NO fuente de verdad: si un cliente estaba desconectado se pierde el evento; al reconectar, cada cliente resincroniza con un GET normal. El estado real siempre vive en Postgres.
- Para métricas agregadas (conteos, sumas) preferir un endpoint dedicado que agregue en SQL (`func.count`/`func.sum`) en vez de que el cliente baje todas las filas y cuente en Python -- ver `GET /pesadas/estadisticas` (`pesaje_service.obtener_estadisticas_dashboard`) vs. `listar_pesadas_completadas`, que sí trae filas completas porque el kardex las necesita entera. El primero no debe crecer con el tamaño de la tabla; el segundo sí, a propósito.

### GUI (`gui/`, `client/`)

- `client/ws_client.py` corre el socket en un hilo daemon aparte que **nunca** toca Tkinter directamente (Tcl/Tk no garantiza que llamar `widget.after()` desde otro hilo sea seguro — causa conocida de cuelgues intermitentes, sobre todo en Windows). El hilo del socket solo escribe a una `queue.Queue`; el hilo principal se reprograma con `after()` para vaciarla.
- Reconexión con backoff exponencial (1s → 30s tope).
- `client/api_client.py` usa timeouts asimétricos a propósito: `connect` corto (4s) porque si no hay ni conexión TCP no vale la pena esperar; `read` más permisivo (12s) para no cortar reportes grandes (kardex/Excel).
- **Carga de datos de pantalla: siempre asíncrona, vía `gui/async_utils.cargar_en_hilo()`.** Cada pantalla se construye al instante (esqueleto vacío o con placeholders "…") y sus llamadas a `api_client` corren en un hilo de fondo; el resultado se entrega al hilo principal por `after()`, igual que `ws_client.py`. Esto es así porque `gui/app.navegar()` destruye y reconstruye la pantalla completa en cada navegación — si la construcción bloqueara con HTTP síncrono, cualquier hipo de red (antivirus, Wi-Fi de planta) congelaba la ventana entera sin feedback. Al agregar una pantalla nueva o un fetch nuevo en una existente, seguir el patrón: separar "construir esqueleto" de "cargar y poblar", y usar `cargar_en_hilo()` para lo segundo. Las excepciones deliberadas (guardar, aprobar/rechazar, clic en una fila de una tabla) se dejan síncronas a propósito -- ahí una pausa breve es la UX esperada de una acción explícita, no el costo de simplemente cambiar de pantalla.
- Ojo con `self.after(ms, self._callback)` en bucle (polling propio, no `cargar_en_hilo`): si la pantalla se destruye (navegación) sin cancelar el `after_id` con `after_cancel()`, el timer sigue vivo para siempre referenciando widgets muertos -- cada visita a esa pantalla deja un timer fantasma más corriendo de fondo. Ver `destroy()` overrideado en `pesaje_entrada_view.py`/`pesaje_salida_view.py` (polling de peso de báscula) como el patrón a seguir para cualquier `self.after()` autoreprogramado nuevo.
- Los íconos de la UI son caracteres Unicode simples (flechas `↓ ↑ ← →`, formas geométricas `● ◆ ▲`), no emoji con selector de variación (`️` U+FE0F) ni glifos del bloque "Miscellaneous Symbols and Arrows" (`⬇⬆` U+2B07/2B06) -- esos no tienen glifo en la fuente que usa Tkinter en Windows y se ven como recuadros vacíos ("tofu boxes"). Si un ícono nuevo se ve como un cuadrado roto al probarlo, es señal de estar fuera del rango seguro.
- Todo `ctk.CTkFont(...)` en `gui/` debe fijar `family=UI["fuente"]` explícitamente, igual que los estilos de `ttk.Treeview` deben usar `"Segoe UI"` (no `"Helvetica"`). CustomTkinter cae en su propia fuente empaquetada ("Roboto" en Windows, ver `ThemeManager.theme["CTkFont"]`) cuando no se especifica `family` -- una pantalla nueva que se olvide de esto se va a ver con una tipografía distinta al resto de la app aunque use el mismo `UI["fuente"]` en todo lo demás.

### Hardware (`hardware/`)

- `hardware/display_manager.py` es el único punto de entrada al hardware de pesaje — el resto del sistema nunca debe importar los drivers (`display_toledo.py`, `display_simulator.py`) directamente, para poder cambiar de marca de báscula sin tocar el resto del código (patrón Strategy vía `hardware/base_display.py`).
- El display de báscula es **local a la estación Romana** — no pasa por el backend, solo el peso final capturado.
- Driver Toledo (`hardware/display_toledo.py`) habla por puerto serie RS-232 (cable DB9) vía `pyserial`, 8 bits de datos / sin paridad / 1 bit de stop, 9600 baudios por defecto. Protocolo ASCII simple: se envía `W\r\n` y el display responde algo como `+  025340 KG ST\r\n` (signo, peso, unidad, estado estable/inestable).
- Configuración de marca/puerto/baudrate en `config.py` → diccionario `DISPLAY`. Si la conexión real falla al arrancar (`main.py`), el sistema cae automáticamente al `DisplaySimulador` para no bloquear el arranque.

## Comandos

```bash
pip install -r requirements.txt
```

**Backend** (una sola vez, en la máquina "servidor"):

```bash
python run_server.py
```

Antes del primer arranque en una base de datos nueva:

```bash
alembic upgrade head
```

Si la base de datos ya existía de antes de introducir Alembic (tablas creadas por `database/seed.py`), marcar el baseline sin ejecutarlo:

```bash
alembic stamp head
```

Sembrar datos iniciales (usuarios por defecto, configuración, catálogo de ejemplo) una sola vez en una BD nueva:

```bash
python -m database.seed
```

**GUI** (en cada estación física — Romana y Centro de Costos):

```bash
python main.py
```

Cada estación necesita ver al backend por red — configurar `API_BASE_URL` en `config.py` o exportar `ROMANA_API_URL`. En Windows, `ejecutar.bat` / `ejecutar_servidor.bat` activan el venv y lanzan `main.py` / `run_server.py` respectivamente.

`main.py` verifica el backend antes de abrir la GUI (`_asegurar_backend()`) y, si `API_BASE_URL` apunta a `localhost`/`127.0.0.1` y no responde, lo arranca solo como subproceso (`run_server.py`) y lo cierra al salir — pensado para correr todo en una sola máquina sin levantar dos procesos a mano. Si `API_BASE_URL` apunta a otra máquina (estaciones reales de planta), esto no hace nada; ahí el backend se levanta aparte, en el servidor.

**Tests:**

```bash
pytest backend/tests/
```

Corre contra un SQLite de archivo aislado (`backend/tests/conftest.py` fija `ROMANA_DATABASE_URL` a nivel de módulo antes de cualquier import de `database`/`services`/`backend`) — no requiere Postgres levantado. Las migraciones Postgres-only (pg_trgm) se auto-excluyen en SQLite.

Para un test puntual:

```bash
pytest backend/tests/test_flujo_pesaje.py::test_nombre_del_test
```

## Configuración (`config.py`)

Centraliza todo: conexión a BD (`DATABASE_URL`, override con `ROMANA_DATABASE_URL`), datos de empresa, config del display de báscula (`DISPLAY`), config física de la báscula (`BASCULA`: capacidad, división, unidad), formato de tickets, paleta de la UI, y config del backend (`JWT_SECRET_KEY`, `API_HOST`, `API_PORT`, `API_BASE_URL` — todos overrideables por variable de entorno con prefijo `ROMANA_`).

## Conexión física de la báscula (pendiente de validar en sitio)

La báscula (display Toledo) de la estación Romana se conecta a la PC por **cable serial DB9 (RS-232)** — confirmado por el usuario el 2026-07-14. Coincide con la configuración 8N1 ya implementada en `hardware/display_toledo.py`. Falta probar la conexión real en planta: al hacerlo, verificar en `config.py` → `DISPLAY` que `marca="Toledo"` y que `puerto` apunte al COM correcto (usar Administrador de dispositivos de Windows para identificarlo, especialmente si se usa un adaptador USB-serial en vez de un puerto DB9 nativo).

## Notas de sesión (2026-07-15)

- **Consistencia tipográfica en toda la GUI**: la mitad de las pantallas (Dashboard, Kardex, Corte, los 5 Maestros, Usuarios) no fijaban `family=UI["fuente"]` en sus `CTkFont`, así que se veían con la fuente por defecto de CustomTkinter ("Roboto") en vez de Segoe UI como el resto. Corregido en 13 archivos de `gui/`; ver la convención agregada arriba en la sección de GUI.
- **Permiso `reportes_exportar`** (`services/auth_service.PERMISOS`) ahora incluye nivel 3 (Operador Romana), no solo Admin/Supervisor -- Romana necesita poder exportar PDF/Excel del Kardex, no solo el ticket individual.
- **Atajo "Hoy" en Kardex** (`gui/pesaje/kardex_view.py`): pone Desde=Hasta=fecha actual y filtra directo, para el reporte de fin de día sin escribir la fecha a mano.
- **Búsqueda de conductor en Entrada de Camión** (`gui/pesaje/pesaje_entrada_view.py`): el campo Cédula ahora tiene el mismo patrón de búsqueda que Vehículo (botón "🔍 Buscar" contra el maestro de conductores) -- si existe, autocompleta el nombre y guarda `conductor_id` (antes el campo "Nombre del conductor" se tipeaba pero nunca se enviaba al backend, se perdía siempre).
- Se sembraron datos de simulación en la BD de desarrollo (Postgres local, no parte de este commit): 6 vehículos, 6 conductores y 6 pesadas repartidas en todos los estados de la máquina de estados, para poder probar Dashboard/Kardex/Centro de Costos/Completar Pesaje con datos reales.
- Empaquetar la GUI como `.exe` con PyInstaller queda pendiente a propósito hasta que el sistema esté técnicamente completo (ver checklist tratada en sesión: falta sobre todo validar la báscula física en planta).
