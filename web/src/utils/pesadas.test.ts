import { describe, expect, it } from 'vitest'
import type { Pesada } from '../types/pesada'
import { diferenciaConGuia, formatearKg } from './pesadas'

function pesada(peso_neto: number | null, peso_guia: number | null): Pesada {
  return { peso_neto, peso_guia } as Pesada
}

describe('diferenciaConGuia', () => {
  it('calcula el porcentaje igual que el backend (|neto - guía| / guía)', () => {
    // Mismo cálculo que capturar_peso_salida en services/pesaje_service.py.
    expect(diferenciaConGuia(pesada(11_000, 10_000))).toBeCloseTo(10)
    expect(diferenciaConGuia(pesada(9_000, 10_000))).toBeCloseTo(10)
    expect(diferenciaConGuia(pesada(10_000, 10_000))).toBe(0)
  })

  it('no divide por cero ni inventa números si falta el peso guía', () => {
    expect(diferenciaConGuia(pesada(5_000, 0))).toBeNull()
    expect(diferenciaConGuia(pesada(5_000, null))).toBeNull()
    expect(diferenciaConGuia(pesada(null, 10_000))).toBeNull()
  })
})

describe('formatearKg', () => {
  it('separa los miles', () => {
    expect(formatearKg(12_345)).toMatch(/12[.,\s]345/)
  })

  it('no muestra decimales (la báscula pesa de a 20 kg)', () => {
    expect(formatearKg(1_234.6)).not.toContain(',6')
  })

  it('devuelve — si no hay peso, en vez de "0"', () => {
    expect(formatearKg(null)).toBe('—')
  })
})
