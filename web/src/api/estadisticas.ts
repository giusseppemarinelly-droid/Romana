import type { EstadisticasSeries } from '../types/estadisticas'
import { getJson } from './pesadas'

/** Indicadores y series ya agregados en el backend (nunca se bajan las pesadas crudas para sumarlas acá). */
export const obtenerEstadisticas = (token: string, dias = 14) =>
  getJson<EstadisticasSeries>(`/pesadas/estadisticas/series?dias=${dias}`, token)
