import { ESTADO_POR_CLAVE } from './estados'

// Etiqueta y punto de cada valor de `Pesada.estado` tal como lo manda el
// backend (la máquina de estados de database/models.py). utils/estados.ts
// está indexado por cola del tablero, que no incluye "anulado": acá se
// reusan esas mismas etiquetas y colores y se agrega el que falta, para
// que una pesada se vea igual en el tablero, el historial y el detalle.
export const ESTADOS_PESADA: { valor: string; etiqueta: string; punto: string }[] = [
  { valor: 'en_planta', ...sinClave('enPlanta') },
  { valor: 'pendiente_aprobacion', ...sinClave('pendientesAprobacion') },
  { valor: 'aprobado', ...sinClave('aprobadas') },
  { valor: 'rechazado', ...sinClave('rechazadas') },
  { valor: 'completado', ...sinClave('completadas') },
  // Mismo punto que "En planta": el color no la distingue, la palabra sí.
  { valor: 'anulado', etiqueta: 'Anulada', punto: 'bg-muted' },
]

function sinClave(clave: keyof typeof ESTADO_POR_CLAVE) {
  const { etiqueta, punto } = ESTADO_POR_CLAVE[clave]
  return { etiqueta, punto }
}

/** Estado desconocido (uno nuevo del backend que la web todavía no conoce): se muestra tal cual. */
export function estadoDePesada(estado: string): { etiqueta: string; punto: string } {
  return ESTADOS_PESADA.find((e) => e.valor === estado) ?? { etiqueta: estado, punto: 'bg-muted' }
}

const TIPOS: Record<string, string> = {
  // Mismos nombres que components/Graficos.tsx.
  GENERAL: 'Pesaje General',
  PRODUCTO_TERMINADO: 'Producto Terminado',
}

export function nombreTipoPesaje(tipo: string): string {
  return TIPOS[tipo] ?? tipo
}
