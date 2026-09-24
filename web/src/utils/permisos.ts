/**
 * Espejo de services/auth_service.PERMISOS, solo con lo que usa la web.
 * El backend sigue siendo la autoridad real (cada endpoint valida su
 * permiso); esto es solo para no mostrar secciones o botones que después
 * responderían 403. Si cambia un permiso allá, cambiarlo acá.
 *
 * Niveles: 1=Administrador, 2=Supervisor, 3=Operador Romana, 4=Centro de Costos.
 */
export const PERMISOS = {
  centro_costos: [1, 2, 4], // aprobar / rechazar
  pesaje_ver_pendientes_cc: [1, 2, 3, 4],
  reportes_ver: [1, 2, 3], // kardex, ticket PDF
  maestros_ver: [1, 2, 3],
} as const

export type Permiso = keyof typeof PERMISOS

export function puede(nivel: number, permiso: Permiso): boolean {
  return (PERMISOS[permiso] as readonly number[]).includes(nivel)
}
