import { describe, expect, it } from 'vitest'
import type { Pesada } from '../types/pesada'
import { estaDemorada, UMBRALES_DEMORA_MIN } from './demoras'

const AHORA = new Date('2026-09-22T15:00:00')

function pesada(minutosAtras: number, campo: 'fecha_entrada' | 'fecha_captura'): Pesada {
  // Solo interesa la fecha; el resto de la pesada no lo mira esta función.
  return {
    [campo]: new Date(AHORA.getTime() - minutosAtras * 60_000).toISOString(),
  } as unknown as Pesada
}

describe('estaDemorada', () => {
  it('marca un camión que lleva demasiado en planta', () => {
    const limite = UMBRALES_DEMORA_MIN.enPlanta
    expect(estaDemorada(pesada(limite - 1, 'fecha_entrada'), 'enPlanta', AHORA)).toBe(false)
    expect(estaDemorada(pesada(limite + 1, 'fecha_entrada'), 'enPlanta', AHORA)).toBe(true)
  })

  it('marca una pesada que Costos tiene esperando hace mucho', () => {
    const limite = UMBRALES_DEMORA_MIN.esperandoCostos
    expect(estaDemorada(pesada(limite + 1, 'fecha_captura'), 'esperandoCostos', AHORA)).toBe(true)
  })

  it('no marca nada si falta la fecha (no se puede afirmar que haya demora)', () => {
    expect(estaDemorada({ fecha_entrada: null } as Pesada, 'enPlanta', AHORA)).toBe(false)
  })

  it('no marca las columnas que no tienen umbral (completadas)', () => {
    expect(estaDemorada(pesada(10_000, 'fecha_entrada'), 'completadas', AHORA)).toBe(false)
  })
})
