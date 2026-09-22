# Tasks: Web de Supervisión (solo lectura)

Ver `tasks/plan.md` para el resumen y `docs/SPEC-web-supervision.md`
para el spec completo.

## Phase 1: Fundación

### Task 1: Scaffold del proyecto web (Vite + React + TS + Tailwind)

**Description:** Crear `web/` con Vite+React+TS y Tailwind configurado
con la paleta de marca (navy `#1E2B50`, ámbar `#C1802A`, mismos tokens
que `config.py` UI), ESLint básico.

**Acceptance criteria:**
- [x] `cd web && npm install && npm run dev` levanta un placeholder en el navegador (HTTP 200 desde WSL y desde Windows) — consola del navegador pendiente de ojo humano
- [x] `npm run build` genera `web/dist/` sin errores
- [x] Colores de marca disponibles como clases Tailwind (verificado en el CSS generado)

**Verification:**
- [x] `npm run build` sale limpio; `npm run lint` sale limpio
- [ ] Manual: abrir `localhost:5173` y confirmar que carga — **pendiente del usuario**

**Dependencies:** None

**Files touched:**
- `web/package.json`, `web/vite.config.ts` (+ proxy /api y /ws), `web/src/index.css` (tokens `@theme` de Tailwind v4 — no hay `tailwind.config.js` en v4)
- `web/src/main.tsx`, `web/src/App.tsx`, `web/index.html`, `web/tsconfig.app.json` (+ `strict`), `web/README.md`, `web/public/favicon.ico`

**Estimated scope:** Small

---

### Task 2: Login funcional contra el backend real

**Description:** Página de Login que llama `POST /api/v1/auth/login`,
guarda el JWT, redirige a un dashboard placeholder si el login es
exitoso. Bloquea niveles fuera de 1-2 con mensaje claro propio de la
web (el backend ya protege cada endpoint aparte, esto es solo UX).

**Acceptance criteria:**
- [x] Login con `admin`/`admin123` funciona y persiste el token (en `sessionStorage` — dura mientras la pestaña esté abierta, ver Risks en plan.md)
- [x] Login con `operador`/`oper123` (nivel 3) muestra aviso de acceso restringido, no entra (también `centrocostos`, nivel 4)
- [x] Credenciales inválidas muestran el mismo mensaje genérico que ya usa el backend (sin enumeración de usuarios)

**Verification:**
- [x] Contra el backend real, a través del proxy de Vite, desde WSL y desde Windows: los 4 roles + una credencial inválida
- [x] `npm run test`: 15/15 (login, niveles, errores, sin red, JWT real decodificado: vence en 12.00h)
- [ ] Manual: probar el login en el navegador — **pendiente del usuario**

**Dependencies:** Task 1

**Files touched:**
- `web/src/pages/Login.tsx`, `web/src/pages/Dashboard.tsx` (provisorio, se completa en Tarea 4)
- `web/src/api/auth.ts` (+ `.test.ts`), `web/src/hooks/useSesion.ts` (+ `.test.ts`)
- `web/src/types/auth.ts`, `web/src/components/IconoBalanza.tsx`, `web/src/App.tsx`
- `web/vite.config.ts` (config de Vitest), `web/package.json` (scripts test, engines), `web/.nvmrc` (Node 24)

**Estimated scope:** Small → terminó en Medium (sumó el paso a Node 24 y la sesión con vencimiento)

---

### Task 3: Servir la SPA desde el backend (StaticFiles)

**Description:** Montar `web/dist/` en `backend/main.py` vía
`StaticFiles`, en una ruta que no choque con `/api/v1/*` ni
`/ws/*`.

**Decisión tomada con evidencia:** montada bajo `/supervision/`, **no en
la raíz**. Comprobado con Starlette 0.41: montada en `/`, el StaticFiles
se queda con los requests que ninguna ruta matchea del todo y un GET a
una ruta solo-POST pasa de `405` a `404` — rompía "la API sigue
exactamente igual". La raíz `/` redirige (GET y HEAD) a `/supervision/`.
Si `web/dist` no está compilado, no se monta nada y el backend arranca
igual (las estaciones de pesaje dependen de él).

**Acceptance criteria:**
- [x] Con `npm run build` ya corrido, `python run_server.py` sirve la SPA en `http://<host>:8000/supervision/` (y `/` redirige ahí)
- [x] `/api/v1/...` y `/ws/pesadas` siguen funcionando exactamente igual que antes (405/404 JSON idénticos, WebSocket en vivo con token real)

**Verification:**
- [x] `pytest backend/tests/`: 67/67 (62 previos + 5 nuevos en `test_web_supervision.py`), con y sin `web/dist` compilado
- [x] En vivo: HTML/JS/CSS/favicon 200, `charset=utf-8`, API sin cambios, WebSocket abre con token válido
- [ ] Manual: abrir `http://127.0.0.1:8000/` en el navegador y ver el login — **pendiente del usuario**

**Dependencies:** Task 1

**Files touched:**
- `backend/main.py` (`montar_web_supervision`), `config.py` (`WEB_DIST_DIR`)
- `backend/tests/test_web_supervision.py` (nuevo), `web/vite.config.ts` (`base: '/supervision/'`)

**Estimated scope:** Small

---

## Checkpoint: Fundación
- [x] `npm run build` + `python run_server.py` sirven el login real desde un solo proceso
- [x] Login funciona con las 4 credenciales sembradas (bloquea niveles 3-4 con mensaje claro)
- [x] `pytest backend/tests/` en verde (67/67 — los 62 originales intactos + 5 nuevos)
- [x] **Revisar con el usuario antes de seguir** — aprobado el 2026-09-22 ("se ve bien"); la Fase 2 arranca cuando el usuario avise

## Phase 2: Vistas en vivo

### Task 4: Tablero de Estados en vivo

**Description:** Página principal (post-login) con las pesadas
agrupadas por estado (en_planta / pendiente_aprobacion / aprobado /
completado) en columnas tipo kanban con conteo por columna. Conectada
al WebSocket vía `useWebSocket`, se refresca sola con eventos
relevantes.

**Resuelto al empezar:** no hizo falta ningún endpoint nuevo. Ya existen
`/pesadas/en-planta`, `/pendientes-aprobacion`, `/aprobadas-pendientes` y
`/completadas?limit=`, los cuatro accesibles para Admin/Supervisor.

**Acceptance criteria:**
- [x] Las 4 columnas muestran las pesadas reales de la base (verificado contra la BD de desarrollo: 3 esperando aprobación, 3 completadas)
- [ ] Registrar una entrada desde la app de escritorio hace aparecer la pesada en "en_planta" sin recargar — **pendiente del usuario** (prueba de dos ventanas)
- [x] Si el WebSocket se corta, reconecta solo con backoff 1s→30s (probado con temporizadores simulados: crece, se corta al conectar, tope de 30s, no reconecta al desmontar)

**Verification:**
- [x] 40 tests en verde, incluidos: hook de WebSocket (8 casos), cálculos de tiempo, y render real de las dos pantallas en DOM simulado
- [ ] Manual: dos ventanas lado a lado (escritorio + navegador), registrando una entrada real — **pendiente del usuario**

**Dependencies:** Task 2

**Files touched:**
- `web/src/pages/Dashboard.tsx`, `web/src/components/TableroEstados.tsx`, `TarjetaPesada.tsx`, `Encabezado.tsx`, `EstadoConexion.tsx`
- `web/src/hooks/useWebSocket.ts` (+test), `useDatosEnVivo.ts`, `web/src/api/pesadas.ts`, `web/src/types/pesada.ts`, `web/src/utils/tiempo.ts` (+test)

**Estimated scope:** Medium

---

### Task 5: Módulo Costos (solo lectura)

**Description:** Página que reusa los endpoints existentes de
pendientes de aprobación y auto-aprobadas (los mismos que ya consumen
`gui/centro_costos/centro_costos_view.py` y `auto_aprobadas_view.py`)
en dos listas de solo lectura. Ningún control de decisión.

**Acceptance criteria:**
- [x] La cola de pendientes sale del mismo endpoint que consume la estación de escritorio (`/pesadas/pendientes-aprobacion`), así que no puede diferir
- [x] Cero llamadas POST/PUT/PATCH en el código de esta página o lo que importa (verificado por grep y por un test que falla si aparece una)

**Verification:**
- [x] Test que renderiza Costos y comprueba que no existe ningún botón de aprobar/rechazar/anular, y que todos los requests son GET
- [x] `grep` sobre `web/src`: el único método de escritura en toda la web es el POST del login
- [ ] Manual: comparación en vivo contra la pantalla de escritorio — **pendiente del usuario**

**Dependencies:** Task 2

**Files touched:**
- `web/src/pages/Costos.tsx`, `web/src/components/Navegacion.tsx`, `web/src/utils/pesadas.ts` (+test)
- `web/src/App.tsx` (navegación entre pantallas), `web/src/api/pesadas.ts`

**Nota:** navegación por estado, sin router — `react-router` habría sido
una dependencia nueva fuera de lo acordado. La contra: no hay enlaces
directos a cada pantalla ni botón "atrás". Revisar si aparecen más
pantallas.

**Estimated scope:** Small

---

## Checkpoint: Vistas en vivo
- [x] Tablero de Estados y Costos muestran datos reales (verificado contra la BD de desarrollo) y se recargan ante cualquier evento del WebSocket
- [x] Cero escritura verificado (grep + test automático que falla si aparece una)
- [ ] Falta la prueba de dos ventanas (escritorio + navegador) — **pendiente del usuario**
- [ ] **Revisar con el usuario antes de seguir a gráficos**

## Phase 3: Analítica

### Task 6: Endpoint de estadísticas agregadas (backend)

**Description:** Nueva función `obtener_estadisticas_series()` en
`services/pesaje_service.py`: tiempo promedio de liberación
(fecha_salida - fecha_entrada) de los últimos N días, volumen de
pesadas completadas por día, distribución por tipo_pesaje. Expuesta en
`GET /api/v1/pesadas/estadisticas/series` (nuevo, aditivo).

**Ampliado a pedido del usuario (2026-09-22):** además de las 3 series,
el endpoint devuelve los indicadores del día (camiones en planta,
esperando a Costos, liberación promedio de hoy, cerradas hoy + kg netos,
% de aprobación automática).

**Acceptance criteria:**
- [x] El endpoint responde con los 3 datasets + indicadores, listos para graficar sin transformación pesada del lado del cliente
- [x] Cálculo de diferencias de fecha en Python sobre una consulta acotada a la ventana pedida, no SQL de un dialecto (portable SQLite/Postgres); `dias` acotado a 90 en el endpoint
- [x] Tests nuevos: promedio por día, exclusión de anuladas, pesadas sin fecha de entrada que no hunden el promedio, días vacíos presentes, distribución por tipo, y el endpoint (401 sin sesión, 422 con rango absurdo)

**Verification:**
- [x] `pytest backend/tests/test_estadisticas_series.py`: 6/6
- [x] `pytest backend/tests/`: 73/73 (67 previos + 6)
- [x] En vivo contra la BD de desarrollo: serie con días vacíos incluidos, promedios reales (28.2 min / 16.2 min), distribución por tipo

**Dependencies:** None

**Files touched:**
- `services/pesaje_service.py` (`obtener_estadisticas_series`), `backend/routers/pesadas.py`
- `backend/schemas/pesada.py`, `backend/tests/test_estadisticas_series.py`

**Estimated scope:** Medium

---

### Task 7: Los 3 gráficos (frontend)

**Description:** `GraficoTiempoLiberacion`, `GraficoVolumenDiario`,
`GraficoDistribucionTipo` con Recharts, consumiendo el endpoint de
Task 6, integrados en el Dashboard con tarjetas de KPI arriba (ej.
"Promedio de liberación: 2h 15min").

**Ampliado a pedido del usuario:** además de los 3 gráficos, fila de
indicadores arriba, avisos de demora en las tarjetas, y quinta columna
de rechazadas en el tablero.

**Acceptance criteria:**
- [x] Los 3 gráficos renderizan con datos reales, no mockeados
- [x] Colores de marca, no los de Recharts por defecto
- [x] Indicadores arriba del tablero (5 tarjetas)
- [x] Camiones demorados resaltados (4 h en planta, 1 h esperando a Costos, 30 min aprobadas sin cerrar) — con reloj además del color, no solo color
- [x] Quinta columna "Rechazadas" (vía `kardex/buscar?estado=rechazado`, sin endpoint nuevo)

**Verification:**
- [x] 52 tests de la web en verde, incluidos: gráficos dibujados, estado "sin datos suficientes" en vez de gráfico vacío, indicadores con los números formateados, y las 5 columnas
- [ ] Manual en el navegador — **pendiente del usuario**

**Dependencies:** Task 4, Task 6

**Files touched:**
- `web/src/components/Graficos.tsx` (+test), `TarjetaKPI.tsx`, `TableroEstados.tsx`, `TarjetaPesada.tsx`
- `web/src/api/estadisticas.ts`, `web/src/api/pesadas.ts`, `web/src/types/estadisticas.ts`
- `web/src/utils/demoras.ts` (+test), `web/src/utils/tiempo.ts`, `web/src/pages/Dashboard.tsx`

**Nota de rendimiento:** Recharts pesa más que el resto de la app junta,
así que se carga aparte (lazy): paquete principal 243 kB (75 kB
comprimido) y gráficos 408 kB (116 kB) que llegan después del tablero.

**Estimated scope:** Medium → Large (por los agregados)

---

## Checkpoint: Completo
- [x] Los 6 puntos de "Success Criteria" del spec están cumplidos (falta solo la verificación manual en vivo del usuario)
- [x] `pytest backend/tests/` en verde: **73/73**; web: **52/52**
- [ ] **Revisión final con el usuario**

## Agregados fuera del plan original (pedidos el 2026-09-22)
- [x] Quinta columna "Rechazadas" en el tablero
- [x] Fila de indicadores del día
- [x] Avisos de demora por camión
- [ ] Ranking de clientes/vehículos — **no hecho a propósito**: se acordó
      dejarlo para cuando se vea si hace falta
