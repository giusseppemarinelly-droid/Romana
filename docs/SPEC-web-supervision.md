# Spec: Web de Supervisión (solo lectura)

Fase Specify de `spec-driven-development`. Precedida por `idea-refine`
(ver `docs/ideas/web-supervision.md` para el proceso de decisión
completo). Módulo único, no bundle — no hizo falta capability map.

## Objetivo

Un supervisor (nivel 1-2, mismas credenciales que ya usan para las
apps de escritorio) entra desde un navegador, en la red interna de la
planta, y ve en vivo: el flujo de camiones por estado, el módulo
"Costos" (cola de aprobación + auto-aprobadas, solo lectura) y
gráficos de estadísticas (tiempo promedio de liberación, volumen
diario, distribución por tipo de pesaje). Nunca escribe nada — el
software de escritorio de Romana sigue siendo el único punto de
pesaje y decisión real.

**Éxito medible:**
- Login funciona con las credenciales de escritorio existentes, sin
  tocar `services/auth_service.py`.
- El tablero de estados se actualiza solo (WebSocket), sin botón de
  refrescar, con la misma latencia que ya tienen las pantallas de
  escritorio (best-effort, reconecta con backoff si se cae la red).
- Los 3 gráficos del MVP muestran datos reales de la base, agregados
  en SQL (no bajando filas crudas al navegador para sumar en JS).
- Cero endpoints nuevos de escritura. Cero cambios a los endpoints que
  ya usan las apps de escritorio (solo endpoints nuevos, aditivos).
- Los 62 tests de `backend/tests/` siguen pasando sin cambios.

### Alcance ampliado (2026-09-22, a pedido del usuario)

Sobre lo anterior se agregaron, sin cambiar ninguna regla del spec
(sigue siendo todo de solo lectura):

- **Quinta columna "Rechazadas"** en el tablero — el camión sigue en
  planta esperando que Romana lo vuelva a pesar. Sale del kardex
  filtrando por estado, sin endpoint nuevo.
- **Indicadores del día** arriba del tablero: camiones en planta,
  esperando a Costos, liberación promedio de hoy, cerradas hoy con sus
  kg netos, y % que se aprueba solo sin pasar por Costos.
- **Avisos de demora**: se resalta el camión que lleva más tiempo del
  esperado en su estado (4 h en planta, 1 h esperando a Costos, 30 min
  aprobado sin cerrar). Umbrales en `web/src/utils/demoras.ts`; si
  alguna vez hay que cambiarlos sin recompilar, el lugar natural sería
  la tabla de Configuración, como la tolerancia de aprobación.
- **No se hizo** el ranking de clientes/vehículos: se acordó dejarlo
  para cuando se vea si hace falta.

## Tech Stack

| Capa | Elección | Por qué |
|---|---|---|
| Framework UI | React 19 + TypeScript 6 | Pedido explícito ("buenos frameworks, profesional"); tipado fuerte (`strict`) para reflejar los schemas Pydantic del backend sin sorpresas en runtime. El spec original decía React 18 — el template actual de Vite trae 19, estable, se dejó. |
| Build | Vite 8 | Estándar de facto para React+TS hoy, arranque rápido, config mínima. Pide Node ≥ 20.19. |
| Gráficos | Recharts | Declarativo, buen soporte TS, mucho más simple que D3 crudo, no tan pesado como Nivo. |
| Estilos | Tailwind CSS v4 | Llega a "profesional" rápido sin escribir un sistema de diseño CSS desde cero. v4 se configura en CSS (`@theme` en `src/index.css`), no en `tailwind.config.js`. |
| Tiempo real | `WebSocket` nativo del navegador | Ya no hace falta librería -- `backend/ws/router.py` autentica por query param (`?token=`), que es exactamente lo que el WebSocket nativo del browser puede mandar sin trucos. |
| Testing | Vitest 5 + jsdom (+ React Testing Library cuando haga falta testear hooks con estado, Tarea 4) | Mismo motor que Vite, cero config extra. Alcance: hooks y transformaciones de datos, no UI completa (ver Testing Strategy). |
| Runtime de desarrollo | Node 24 LTS (fijado en `web/.nvmrc` y `engines`) | Node 20 llegó a fin de soporte en abril 2026, y Vitest 5 / jsdom 30 ya piden Node ≥22. |
| Servido por | FastAPI `StaticFiles`, mismo proceso que `backend/main.py` | Un solo servidor, un solo puerto, nada de hosting externo -- coherente con "solo red interna". |

Nada de esto toca `requirements.txt` -- es 100% del lado de `web/`
(Node/npm), separado del entorno Python.

## Commands

```bash
# Desarrollo del frontend (dentro de web/)
cd web
npm install
npm run dev          # Vite dev server, proxy a http://localhost:8000 para /api y /ws
npm run build         # genera web/dist/ -- esto es lo que sirve el backend
npm run test          # Vitest
npm run lint          # eslint

# Backend -- sin cambios en cómo se arranca
python run_server.py
```

En producción (una sola máquina en la red de planta), `web/dist/` se
sirve montado en el mismo FastAPI bajo `/supervision/` -- no hace falta
levantar un servidor HTTP aparte para la SPA.

**`web/dist/` va versionado en git** (decisión del usuario, 2026-09-22):
el servidor de planta nunca necesita Node, alcanza con clonar el repo.
Cualquier cambio en `web/src` se commitea junto con su `web/dist`
recompilado. Ver `tasks/plan.md` (Open Questions) para los detalles de
implementación (`.gitattributes`, exclusión de `dist` en Tailwind).

## Project Structure

```
web/                          # NUEVO -- primer código JS/TS del proyecto
  src/
    api/                      # fetch() tipados a /api/v1/* -- un archivo por recurso
      auth.ts
      pesadas.ts
      estadisticas.ts
    hooks/
      useWebSocket.ts          # conexión + reconexión con backoff, mismo criterio que client/ws_client.py
      useEstadisticas.ts
    components/
      TableroEstados.tsx       # conteos + lista por estado (en_planta, pendiente_aprobacion, ...)
      GraficoTiempoLiberacion.tsx
      GraficoVolumenDiario.tsx
      GraficoDistribucionTipo.tsx
      TarjetaKPI.tsx
    pages/
      Login.tsx
      Dashboard.tsx
      Costos.tsx
    types/
      pesada.ts                # refleja backend/schemas/pesada.py
      auth.ts                  # refleja backend/schemas/auth.py
    App.tsx
    main.tsx
  index.html
  package.json
  vite.config.ts               # + proxy de /api y /ws al backend (solo en `npm run dev`)
  tsconfig.json                # tokens de Tailwind viven en src/index.css (@theme), no hay tailwind.config.js

backend/
  main.py                      # + montar_web_supervision(): sirve web/dist bajo /supervision/
  routers/pesadas.py            # + GET /api/v1/pesadas/estadisticas/series?dias= (nuevo, aditivo, `dias` acotado a 90)
services/
  pesaje_service.py             # + obtener_estadisticas_series(): indicadores + series, ventana acotada
```

## Code Style

Mismo criterio de nombres en español que el resto del proyecto
(`_cargar_vehiculos`, `construir_formulario`, etc.) -- se mantiene
también en TypeScript, componentes y funciones en español, texto de UI
en español (ya lo es en toda la app de escritorio):

```tsx
// GraficoTiempoLiberacion.tsx
export function GraficoTiempoLiberacion({ datos }: { datos: PuntoSerie[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={datos}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="fecha" />
        <YAxis unit=" min" />
        <Tooltip formatter={(v) => `${v} min`} />
        <Line type="monotone" dataKey="minutosPromedio" stroke="#C1802A" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- Componentes funcionales + hooks, nada de clases.
- Un componente por archivo, mismo nombre.
- `types/` refleja 1:1 los schemas Pydantic que ya existen -- si el
  backend agrega un campo, el tipo de TS se actualiza a mano (no hay
  generación automática en el MVP, sería sobre-ingeniería para el
  tamaño de este proyecto).

## Testing Strategy

- **Backend**: los endpoints nuevos de agregación se prueban igual que
  el resto (`backend/tests/`, contra el SQLite aislado que ya usa
  `conftest.py`) -- mismo patrón, nada nuevo que aprender.
- **Frontend**: Vitest + React Testing Library, pero acotado a valor
  real, no cobertura por cobertura:
  - `useWebSocket` (reconexión, parseo de eventos) -- sí, es lógica
    con estados reales que puede romperse en silencio.
  - Transformaciones de datos para los gráficos (agrupar por día,
    calcular promedios) -- sí, son cálculos, no JSX.
  - Componentes puramente visuales (`TarjetaKPI`, layout) -- no,
    verificación visual manual alcanza para un MVP exploratorio.

## Boundaries

- **Siempre**: la única llamada no-GET desde `web/` es
  `POST /api/v1/auth/login` (autenticación — aunque técnicamente
  escribe `last_login` en la base, no toca datos del negocio). Ningún
  otro POST/PUT/PATCH/DELETE, ni un botón, ni un formulario. Si algún
  día "Costos" necesita decidir desde la web, es una decisión nueva y
  explícita, no un agregado silencioso. *(Corregido en la Tarea 2: la
  versión original decía "ningún POST", que el propio login ya
  incumplía.)*
- **Preguntar antes**: cualquier dependencia npm nueva fuera de
  React/TS/Vite/Recharts/Tailwind/Vitest ya acordadas; cambiar el CORS
  actual (`allow_origins=["*"]`) a algo más restrictivo (probablemente
  correcto hacerlo, pero es una decisión de seguridad, no un detalle
  de implementación); exponer el backend fuera de la red interna.
- **Nunca**: tocar `gui/`, `hardware/`, el código RS-232, ni las
  funciones de escritura de `services/pesaje_service.py`
  (`registrar_entrada`, `capturar_peso_salida`, `aprobar_pesada`,
  etc.) para nada de este trabajo. Nunca modificar la forma de una
  respuesta de API que ya consume la GUI de escritorio -- solo sumar
  endpoints nuevos.

## Success Criteria

- [ ] Un usuario nivel 1 o 2 se loguea desde el navegador con las
      credenciales que ya tiene.
- [ ] El tablero de estados se actualiza solo al registrar una entrada
      o completar un pesaje desde la app de escritorio (probado en
      vivo, dos ventanas -- escritorio + navegador -- una al lado de
      la otra).
- [ ] "Costos" muestra la misma cola que el escritorio, sin ningún
      control de decisión visible.
- [ ] Los 3 gráficos del MVP renderizan con datos reales, no mockeados.
- [ ] `pytest backend/tests/` sigue en 62/62 verde.
- [ ] Ningún endpoint nuevo acepta métodos de escritura.

## Open Questions

- Confirmar el supuesto #2 de arriba (tablero por estado vs. detalle
  completo pesada por pesada) antes de la fase de Plan.
- ~~¿El puerto/ruta donde se sirve la SPA importa?~~ **Resuelto en la
  Tarea 3**: mismo `:8000`, pero bajo `/supervision/` y no en la raíz
  como se asumía acá — montada en `/`, cambiaba las respuestas de error
  de la API (405 → 404, comprobado). La raíz redirige a `/supervision/`.

## Sistema de diseño (2026-09-22)

Definido por el usuario al pie de la letra. **Dos temas:** el **claro es el principal** y usa la paleta de la app de escritorio (`config.py` → UI: navy `#1E2B50` en el sidebar, ámbar `#C1802A` como acento, fondo `#F4F1EC`); el **oscuro** es opcional (botón "Modo oscuro" en el sidebar, se recuerda en `localStorage`). La app de escritorio no se toca. Escala cerrada en `web/src/index.css` (`@theme` borra los valores por defecto de Tailwind) y guardia en `web/src/diseno.test.ts`.

- **Colores del tema oscuro:** fondo `#0F172A`, cards `#1E293B`, acento `#2563EB` (hover `#2159D4`, 10% más oscuro), éxito `#10B981`, error `#EF4444`, advertencia `#F59E0B`, texto `#F8FAFC`, texto secundario `#94A3B8`, bordes `#334155`. Blanco solo como texto sobre el acento.
- **Tipografía:** `system-ui` (sin Inter: el servidor de planta no tiene internet y no se agregó dependencia). 24 títulos, 16 subtítulos, 14 texto, 32 bold KPIs.
- **Radios:** 8 botones/campos/filtros, 12 cards y contenedores.
- **Espaciado:** unidad Tailwind = 8px, solo múltiplos. Campos y botones secundarios 40 de alto, botón principal 48, filas de tabla 48, sidebar 240.
- **Contraste (oscuro):** el azul (2.8:1) y el rojo (3.9:1) no llegan a 4.5:1 como texto sobre las cards, así que se usan solo como relleno/punto; los estados son punto de color + texto claro.
- **Conexión:** el indicador del sidebar es la conexión con el **servidor central** (WebSocket), no con la báscula: esa es local a la PC de la Romana y la web no la ve.
- **Estructura:** sidebar fija (Pesajes en vivo / Estadísticas / Costos), KPIs arriba, tablas y gráficos debajo. Recharts se carga solo al entrar a Estadísticas.
