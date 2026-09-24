import { describe, expect, it } from 'vitest'
import { aFechaLocal, fechaHora, ultimosDias } from './fechas'

describe('fechas del historial', () => {
  it('formatea en hora local, no en UTC', () => {
    // 23:30 local: toISOString() lo pasaría al día siguiente en UTC-4.
    expect(aFechaLocal(new Date(2026, 8, 24, 23, 30))).toBe('2026-09-24')
  })

  it('los últimos 7 días incluyen hoy', () => {
    expect(ultimosDias(7, new Date(2026, 8, 24, 10))).toEqual({ desde: '2026-09-18', hasta: '2026-09-24' })
  })

  it('cruza el cambio de mes', () => {
    expect(ultimosDias(7, new Date(2026, 9, 2)).desde).toBe('2026-09-26')
  })

  it('sin fecha, un guion', () => {
    expect(fechaHora(null)).toBe('—')
    expect(fechaHora('2026-09-24T14:30:00')).toContain('24/09/2026')
  })
})
