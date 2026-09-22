import type { PuntoSerie } from '../types/estadisticas'

/**
 * Totales del período a partir de la serie diaria que ya manda el
 * backend. El promedio de liberación se pondera por la cantidad de
 * cierres de cada día: un día con 1 camión no puede pesar lo mismo que
 * uno con 20.
 */
export function resumirSerie(serie: PuntoSerie[]) {
  const completadas = serie.reduce((total, p) => total + p.completadas, 0)

  const conTiempo = serie.filter((p) => p.minutos_promedio !== null && p.completadas > 0)
  const pesos = conTiempo.reduce((total, p) => total + p.completadas, 0)
  const minutosPromedio =
    pesos === 0
      ? null
      : conTiempo.reduce((total, p) => total + (p.minutos_promedio as number) * p.completadas, 0) / pesos

  return {
    completadas,
    promedioDiario: serie.length === 0 ? 0 : completadas / serie.length,
    minutosPromedio,
  }
}
