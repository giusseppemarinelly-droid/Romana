import type { ClaveEstado } from './tablero'

// El color va solo en el punto, nunca en el texto: sobre las cards, el
// azul y el rojo como texto chico no llegan al contraste mínimo (2.8:1
// y 3.9:1 contra 4.5:1). El texto de la etiqueta va siempre al lado.
export const ESTADOS: { clave: ClaveEstado; etiqueta: string; punto: string }[] = [
  { clave: 'enPlanta', etiqueta: 'En planta', punto: 'bg-muted' },
  { clave: 'pendientesAprobacion', etiqueta: 'Esperando a Costos', punto: 'bg-advertencia' },
  { clave: 'rechazadas', etiqueta: 'Rechazada', punto: 'bg-error' },
  { clave: 'aprobadas', etiqueta: 'Aprobada', punto: 'bg-acento' },
  { clave: 'completadas', etiqueta: 'Completada', punto: 'bg-exito' },
]

export const ESTADO_POR_CLAVE = Object.fromEntries(ESTADOS.map((e) => [e.clave, e])) as Record<
  ClaveEstado,
  (typeof ESTADOS)[number]
>
