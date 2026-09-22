import type { Pesada } from '../types/pesada'

/**
 * Diferencia porcentual entre el peso neto de la báscula y el peso de
 * la guía del transportista -- el número con el que Centro de Costos
 * decide. Mismo cálculo que `capturar_peso_salida` en
 * services/pesaje_service.py: por debajo de la tolerancia configurada
 * (10% por defecto) el backend aprueba solo.
 *
 * Devuelve null si no se puede calcular (sin peso guía no hay contra
 * qué comparar) -- mostrar "—" es más honesto que un 0 o un 100%.
 */
export function diferenciaConGuia(pesada: Pesada): number | null {
  const guia = pesada.peso_guia
  const neto = pesada.peso_neto
  if (!guia || neto === null) return null
  return (Math.abs(neto - guia) / guia) * 100
}

export function formatearKg(kilos: number | null): string {
  if (kilos === null) return '—'
  return kilos.toLocaleString('es-VE', { maximumFractionDigits: 0 })
}
