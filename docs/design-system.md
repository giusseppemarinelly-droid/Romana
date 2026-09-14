# Sistema de diseño — Romana Digital

Spec aprobada el 2026-09-14 (ver conversación de esa fecha para el proceso de decisión). Define la identidad visual de la app — reemplaza la paleta genérica de Tailwind (`blue-700`/`slate-*`) que traía el proyecto desde el inicio.

Fuente de verdad en código: `config.py` → diccionario `UI`. Componentes reutilizables: `gui/components/ui_kit.py`.

## 1. Paleta de color

### Marca / Identidad
El navy real del logo de Sura de Venezuela (muestreado a nivel de píxel de `reports/templates/logo.png`, no a ojo), no un azul genérico de librería.

| Token | Hex | Uso |
|---|---|---|
| `brand.900` (Tinta) | `#1E2B50` | Sidebar, encabezados, texto de máxima jerarquía, botones primarios de navegación |
| `brand.700` | `#28365C` | Hover/presionado sobre elementos navy |
| `brand.050` (tinte) | `#EEF1F8` | Fondo de filas activas/seleccionadas, resaltados sutiles |

### Acción
Un ámbar industrial, deliberadamente NO otro azul — con dos azules (marca + acción) el ojo no distingue "esto es identidad" de "esto se puede tocar". El navy es estructura, el ámbar es "esto se hace ahora".

| Token | Hex | Uso |
|---|---|---|
| `action.500` | `#C1802A` | Botones primarios de acción (Registrar, Capturar Peso, Guardar) |
| `action.600` | `#A2681E` | Hover/presionado |
| `action.050` | `#FBF1E3` | Fondo sutil para resaltar el foco de la pantalla |

### Neutrales
Grises con un pelo de temperatura cálida — no el "slate" frío de Tailwind.

| Token | Hex | Uso |
|---|---|---|
| `neutral.900` | `#211F1D` | Texto principal |
| `neutral.600` | `#5C5750` | Texto secundario/ayuda |
| `neutral.300` | `#D8D3CB` | Bordes |
| `neutral.100` | `#F4F1EC` | Fondo general de la app |
| `neutral.000` | `#FFFFFF` | Superficie de tarjetas |

### Semánticos
Distintos entre sí y del ámbar de acción, para que "peligro"/"éxito" nunca se confundan con "botón normal".

| Token | Hex | Uso |
|---|---|---|
| `success` | `#1F7A4D` | Aprobado, completado, éxito |
| `warning` | `#B5461F` | Diferencia fuera de tolerancia, atención |
| `danger` | `#B42318` | Rechazado, error de validación, anular |
| `info` | `#2A5FA5` | Mensajes informativos neutros |

### Estado de la báscula
Set propio, no reutiliza los semánticos de arriba. Responde al hallazgo pendiente de la auditoría de mostrar siempre qué display está activo. Nunca solo color — siempre acompañado de texto/ícono.

| Estado | Color | Tratamiento |
|---|---|---|
| Conectada, peso estable | `success` `#1F7A4D` | Punto sólido + texto |
| Conectada, leyendo/inestable | `action.500` `#C1802A` | Punto con pulso sutil |
| Sin señal / desconectada | `neutral.600` `#5C5750` | Punto hueco (contorno, no relleno) |
| Error de hardware/dato corrupto | `danger` `#B42318` | Punto sólido + ícono de alerta |

## 2. Tipografía

Segoe UI en todo (ya es requisito del proyecto — ver CLAUDE.md, evita meter una fuente nueva).

| Nivel | Tamaño | Peso | Uso |
|---|---|---|---|
| `display` | 44px | Bold | El peso de la báscula durante la captura — el elemento más grande de toda la app, a propósito |
| `h1` | 22px | Bold | Título de pantalla |
| `h2` | 15px | Bold | Título de sección dentro de una tarjeta |
| `body` | 13px | Regular | Texto de formulario, tablas |
| `label` | 11px | Semibold, mayúsculas, +0.04em de espaciado | Etiquetas de campo ("VEHÍCULO", "PRODUCTO") |
| `caption` | 11px | Regular | Texto de ayuda, timestamps |

## 3. Espaciado

Escala de 4px: **4 · 8 · 12 · 16 · 24 · 32 · 48**. Nada fuera de esta lista.

## 4. Bordes y esquinas

Radios con jerarquía, nunca "todo redondo":
- Inputs, botones, badges: **6px**
- Tarjetas, paneles: **10px**
- Nunca más de 10px en ningún lado

## 5. Elevación

Casi nada de sombra — bordes finos (`1px`, `neutral.300`) en vez de sombra para separar tarjetas del fondo. Una sola sombra reservada para elementos flotantes de verdad (el desplegable de búsqueda de `gui/components/combo_buscable.py`): `0 4px 12px rgba(30,43,80,0.12)`.

## 6. Componentes base (`gui/components/ui_kit.py`)

- **Botón primario**: fondo `action.500`, texto blanco, radio 6px, alto 40px, hover `action.600`.
- **Botón secundario**: fondo transparente, borde `neutral.300` 1px, texto `brand.900`, hover fondo `neutral.100`.
- **Botón peligro**: mismo molde que primario, colores `danger`.
- **Card**: fondo blanco, borde `neutral.300` 1px, radio 10px, padding 24px.
- **Input**: fondo `neutral.100`, borde `neutral.300` 2px, radio 6px, alto 40px, foco → borde `brand.900`.
- **Badge de estado**: pill con radio 6px, punto de color + texto, nunca solo color.
- **PesoDisplay**: el número de peso en `display` (44px) + badge de estado de báscula integrado.

## Rollout

1. ✅ `config.py` (paleta + tipografía + espaciado, mismas claves del diccionario `UI` con valores nuevos — no se tocó la arquitectura de cómo cada pantalla lee sus colores)
2. ✅ `gui/components/ui_kit.py` (componentes base nuevos)
3. ⬜ Piloto: `gui/pesaje/pesaje_entrada_view.py` (pendiente de aprobación del usuario antes de seguir)
4. ⬜ Resto de pantallas, una por una, tras aprobar el piloto

Restricción: solo capa visual/UI. Ninguna lógica de negocio ni de integración con la báscula (RS-232) se tocó en este rollout.
