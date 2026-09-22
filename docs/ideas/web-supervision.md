# Web de Supervisión — Romana Digital

Refinada con la skill `idea-refine` el 2026-09-22. Ver conversación de esa
fecha para el proceso completo (preguntas de sharpening, direcciones
descartadas y por qué).

## Problem Statement
¿Cómo le damos a un supervisor de Sura visibilidad en vivo del pulso de
la planta (flujos de pesaje, aprobaciones, estadísticas) sin que tenga
que pararse frente a una de las dos estaciones de escritorio, y sin
tocar el software de pesaje real?

## Recommended Direction
SPA en React + TypeScript, servida como archivos estáticos desde el
mismo backend FastAPI que ya usan las dos apps de escritorio (Romana y
Centro de Costos) — no se construye backend nuevo, es un tercer cliente
sobre la misma API REST + WebSocket ya existente. Auth reutiliza
`POST /api/v1/auth/login` y el rol Supervisor (nivel 2) que ya existe
en `services/auth_service.PERMISOS`. El módulo "Costos" es de **solo
lectura** — ver estado y auto-aprobadas, nunca decidir desde ahí.
Los gráficos de estadísticas (tiempo promedio de liberación de
camiones, volumen por día, distribución por tipo de pesaje, etc.) viven
**enteramente acá**, no en el dashboard de escritorio — evita meterle
matplotlib (dependencia pesada) al CustomTkinter, y un navegador da
mejores herramientas de gráficos que un Canvas de escritorio de todos
modos.

## Key Assumptions to Validate
- [ ] El broadcast del WebSocket en memoria (`workers=1`) aguanta el
      handful de supervisores que se van a conectar sin degradar el
      broadcast a las 2 estaciones críticas de pesaje -- validar con
      unas cuantas pestañas abiertas antes de darlo por hecho.
- [ ] "Profesional" para el usuario = se ve/navega como un dashboard de
      verdad (cards, gráficos interactivos) -- confirmar con el primer
      mockup antes de construir todo el resto.
- [ ] Montar `StaticFiles` en el FastAPI existente no choca con nada de
      lo que ya sirve ese proceso (rutas `/api/v1/*` y `/ws/*` no se
      pisan con la ruta de la SPA).

## MVP Scope
**Adentro:**
- Login con las credenciales ya existentes (rol Supervisor/Admin).
- Vista de flujo en vivo: pesadas por estado (en_planta,
  pendiente_aprobación, aprobado, completado) actualizándose por WS.
- Módulo "Costos": cola de pendientes + auto-aprobadas, solo lectura.
- Gráficos: tiempo promedio de liberación (fecha_entrada → fecha_salida),
  volumen de pesadas por día (últimos 7-14 días), distribución por tipo
  de pesaje (General vs Producto Terminado).

**Afuera (de este MVP):**
- Aprobar/Rechazar desde la web.
- Acceso remoto fuera de la red de planta.
- Exportar reportes desde la web (ya existe en Kardex de escritorio).
- Cualquier escritura a la base de datos desde este cliente nuevo.

## Not Doing (and Why)
- **Escribir/decidir desde la web** — duplicaría la autoridad de
  decisión que hoy es exclusiva de Centro de Costos (escritorio),
  abriendo la puerta a que dos lugares actúen sobre la misma pesada.
- **Acceso remoto/hosting externo** — no lo pediste, y expondría el
  backend a internet con una config (CORS abierto, JWT pensado para red
  interna) que no está lista para eso.
- **HTMX/server-rendered en vez de SPA** — más simple y sin Node, pero
  no llega al nivel "profesional/buenos frameworks" que pediste
  explícitamente.

## Open Questions
- ¿El login de la web es el mismo usuario/contraseña de escritorio, o
  preferís usuarios separados solo para consulta?
- ¿"Ver flujos en curso" necesita el detalle completo de cada pesada
  (como el panel de Centro de Costos) o alcanza con un tablero tipo
  kanban por estado, sin entrar al detalle?

## Decisión de seguimiento (2026-09-22)
Los gráficos/estadísticas se mueven **enteramente** a esta web nueva —
no se agrega matplotlib ni ningún gráfico al dashboard de escritorio
(CustomTkinter). Confirmado por el usuario.
