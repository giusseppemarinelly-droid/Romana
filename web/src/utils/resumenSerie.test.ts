import { describe, expect, it } from 'vitest'
import { resumirSerie } from './resumenSerie'

describe('resumirSerie', () => {
  it('pondera el promedio de liberación por la cantidad de cierres de cada día', () => {
    const r = resumirSerie([
      { fecha: '2026-09-21', completadas: 1, minutos_promedio: 300 },
      { fecha: '2026-09-22', completadas: 3, minutos_promedio: 100 },
    ])
    // (300*1 + 100*3) / 4 = 150, no (300+100)/2 = 200
    expect(r.minutosPromedio).toBe(150)
    expect(r.completadas).toBe(4)
    expect(r.promedioDiario).toBe(2)
  })

  it('sin tiempos medidos devuelve null, no 0', () => {
    const r = resumirSerie([{ fecha: '2026-09-22', completadas: 0, minutos_promedio: null }])
    expect(r.minutosPromedio).toBeNull()
    expect(r.completadas).toBe(0)
  })
})
