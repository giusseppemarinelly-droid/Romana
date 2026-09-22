# Implementation Plan: Web de Supervisión (solo lectura)

Ver `docs/SPEC-web-supervision.md` para el spec completo y
`docs/ideas/web-supervision.md` para el proceso de idea-refine previo.

## Overview

Primer frontend web del proyecto (React + TypeScript + Vite + Recharts
+ Tailwind), servido por el mismo backend FastAPI que ya usan las apps
de escritorio. Solo lectura: tablero de estados en vivo, módulo
"Costos" de solo lectura, y 3 gráficos de estadísticas. Cero
escritura, cero backend nuevo, cero cambios a los endpoints que ya
consume la GUI de escritorio.

## Architecture Decisions

- **Un solo proceso sirve todo**: `web/dist/` montado como `StaticFiles`
  en `backend/main.py` -- no hay servidor HTTP nuevo que mantener.
- **Autenticación reusada tal cual**: mismo `POST /api/v1/auth/login`,
  mismo JWT, mismo `services/auth_service.PERMISOS` -- el frontend web
  solo bloquea niveles 3-4 en su propia UI (el backend ya protege cada
  endpoint por separado, esto es solo UX).
- **WebSocket nativo del navegador**: `backend/ws/router.py` ya
  autentica por query param, compatible sin cambios.
- **Endpoints nuevos son aditivos**: nada de lo que ya usa la GUI de
  escritorio cambia de forma. El único endpoint nuevo es el de
  estadísticas de series (Task 6).

## Task List

### Phase 1: Fundación

- [x] Task 1: Scaffold del proyecto web (Vite + React + TS + Tailwind)
- [x] Task 2: Login funcional contra el backend real
- [x] Task 3: Servir la SPA desde el backend (StaticFiles) — bajo `/supervision/`, no en `/` (ver todo.md)

### Checkpoint: Fundación
- [x] `npm run build` + `python run_server.py` sirven el login real desde un solo proceso
- [x] Login funciona con las 4 credenciales sembradas (bloquea niveles 3-4 con mensaje claro)
- [x] `pytest backend/tests/` en verde (67/67)
- [x] Revisar con el usuario antes de seguir — aprobado 2026-09-22

### Notas para la Tarea 4 (salieron de la 3)
- **El rechazo de auth del WebSocket llega como código 1006, no 4401.**
  `backend/ws/router.py` llama `websocket.close(4401)` *antes* de
  `accept()`, así que uvicorn rechaza el handshake con HTTP 403 y el
  cliente solo ve una conexión anormal (1006) — ya era así para la app
  de escritorio también. El hook `useWebSocket` no puede distinguir
  "token vencido" de "se cortó la red" por el código de cierre: tiene
  que apoyarse en el vencimiento que ya controla `useSesion`.

### Phase 2: Vistas en vivo

- [x] Task 4: Tablero de Estados en vivo — sin endpoints nuevos, los 4 listados ya existían
- [x] Task 5: Módulo Costos (solo lectura)

### Checkpoint: Vistas en vivo
- [x] Tablero de Estados y Costos muestran datos reales y se recargan por WebSocket
- [x] Cero escritura verificado (grep + test que falla si aparece una)
- [ ] Prueba de dos ventanas (escritorio + navegador) — pendiente del usuario
- [ ] Revisar con el usuario antes de seguir a gráficos

### Phase 3: Analítica

- [x] Task 6: Endpoint de estadísticas agregadas (backend) — + indicadores del día
- [x] Task 7: Los 3 gráficos (frontend) — + indicadores, avisos de demora y quinta columna de rechazadas

### Checkpoint: Completo
- [x] Los 6 puntos de "Success Criteria" del spec están cumplidos
- [x] `pytest backend/tests/` en verde: 73/73; web: 52/52
- [ ] Revisión final con el usuario

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broadcast WS en memoria (`workers=1`) no aguanta más clientes conectados | Medio | Probar Task 4 con varias pestañas abiertas antes de dar la vista por terminada -- si degrada, es señal temprana, no sorpresa en producción. |
| Primera vez que el proyecto tiene tooling de Node/npm | Bajo | Aislado en `web/`, no toca `requirements.txt` ni el entorno Python -- reversible sin dejar rastro. |
| Cálculo de tiempo de liberación con fechas nulas (pesadas sin completar) | Medio | Filtrar explícitamente `estado == "completado"` y `fecha_salida IS NOT NULL`, mismo patrón que `obtener_estadisticas_dashboard()`. |
| **JWT guardado en un navegador** (surgió en Tarea 2). `backend/security.py` eligió JWT-en-header asumiendo "los clientes son apps de escritorio, no navegadores: no hay riesgo de XSS" — con la web eso deja de ser cierto. Y el token de un Admin sirve para TODA la API (incluidas rutas de escritura), aunque la web nunca las use. | Medio | Hecho: `sessionStorage` (muere al cerrar la pestaña, no `localStorage`), sin HTML crudo en React (`dangerouslySetInnerHTML` prohibido), cierre automático al vencer el token. Pendiente, fuera del MVP: un claim/scope de "solo lectura" en el JWT que el backend haga respetar, para que un token robado de la web no pueda escribir. Visto en la Tarea 3: como el WebSocket lleva el JWT en la URL (`?token=`), **uvicorn lo escribe completo en su log de acceso** — ya pasaba con la app de escritorio, pero son tokens válidos por 12h guardados en texto plano en el servidor. |

## Open Questions

- ~~Dónde se corre `npm run build` para producción~~ **Resuelto
  2026-09-22 por el usuario: (c), `web/dist/` versionado en git** — el
  servidor de planta nunca necesita Node. Implementado con:
  - `web/.gitignore` ya no ignora `dist/`.
  - `.gitattributes`: `web/dist/** binary linguist-generated=true` — el
    git de Windows tiene `core.autocrlf=true` y sin esto cambiaría los
    bytes servidos; tampoco intenta diffs/merges (ante conflicto se
    regenera).
  - `src/index.css`: `@source not "../dist"` — Tailwind v4 escanea todo
    lo no ignorado por git, y sin esto leía el build anterior como
    código (+21% de CSS, builds no deterministas). Verificado: hashes
    idénticos a los de antes, en 3 builds seguidos.
  - **Costo de esta opción**: si se cambia `web/src` sin correr
    `npm run build`, el servidor sirve una versión vieja sin avisar.
    Regla: commitear `web/dist/` junto con el cambio de `web/src` que lo
    produjo, nunca por separado (documentado en `web/README.md` y
    `CLAUDE.md`).
- Qué endpoint existente devuelve pesadas agrupables por estado para
  Task 4, o si hace falta uno nuevo -- se resuelve al empezar esa
  tarea revisando `backend/routers/pesadas.py`.
