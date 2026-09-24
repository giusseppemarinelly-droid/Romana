import { puede, type Permiso } from './permisos'

export type Pagina = 'tablero' | 'tickets' | 'estadisticas' | 'costos' | 'maestros'

// `permiso` null = cualquier nivel que haya podido entrar a la web.
export const PAGINAS: { clave: Pagina; texto: string; permiso: Permiso | null }[] = [
  { clave: 'tablero', texto: 'Pesajes en vivo', permiso: null },
  { clave: 'tickets', texto: 'Tickets', permiso: 'reportes_ver' },
  { clave: 'estadisticas', texto: 'Estadísticas', permiso: null },
  { clave: 'costos', texto: 'Costos', permiso: 'centro_costos' },
  { clave: 'maestros', texto: 'Maestros', permiso: 'maestros_ver' },
]

export function paginasPara(nivel: number): Pagina[] {
  return PAGINAS.filter((p) => p.permiso === null || puede(nivel, p.permiso)).map((p) => p.clave)
}
