import { describe, expect, it } from 'vitest'
import { fechaCorta, formatearMinutos, horaCorta, tiempoTranscurrido } from './tiempo'

const AHORA = new Date('2026-09-22T15:00:00')

function hace(minutos: number): string {
  return new Date(AHORA.getTime() - minutos * 60_000).toISOString()
}

describe('tiempoTranscurrido', () => {
  it('redondea a "recién" abajo del minuto', () => {
    expect(tiempoTranscurrido(hace(0.5), AHORA)).toBe('recién')
  })

  it('muestra solo minutos abajo de la hora', () => {
    expect(tiempoTranscurrido(hace(1), AHORA)).toBe('1 min')
    expect(tiempoTranscurrido(hace(45), AHORA)).toBe('45 min')
  })

  it('muestra horas y minutos', () => {
    expect(tiempoTranscurrido(hace(60), AHORA)).toBe('1 h')
    expect(tiempoTranscurrido(hace(135), AHORA)).toBe('2 h 15 min')
  })

  it('pasa a días cuando ya no tiene sentido contar horas', () => {
    expect(tiempoTranscurrido(hace(60 * 24), AHORA)).toBe('1 día')
    expect(tiempoTranscurrido(hace(60 * 50), AHORA)).toBe('2 días')
  })

  it('devuelve — si no hay fecha (pesadas viejas sin ese dato)', () => {
    expect(tiempoTranscurrido(null, AHORA)).toBe('—')
  })

  it('no muestra tiempos negativos si el reloj del servidor va adelantado', () => {
    const futuro = new Date(AHORA.getTime() + 5 * 60_000).toISOString()
    expect(tiempoTranscurrido(futuro, AHORA)).toBe('recién')
  })
})

describe('formatearMinutos', () => {
  it('pasa a horas y minutos', () => {
    expect(formatearMinutos(45)).toBe('45 min')
    expect(formatearMinutos(60)).toBe('1 h')
    expect(formatearMinutos(135)).toBe('2 h 15 min')
  })

  it('redondea los decimales que vienen del promedio', () => {
    expect(formatearMinutos(134.6)).toBe('2 h 15 min')
  })

  it('devuelve — cuando no se pudo calcular el promedio', () => {
    expect(formatearMinutos(null)).toBe('—')
  })
})

describe('fechaCorta', () => {
  it('deja día/mes para el eje de los gráficos', () => {
    expect(fechaCorta('2026-09-22')).toBe('22/09')
  })
})

describe('horaCorta', () => {
  it('muestra hora y minutos en 12h', () => {
    expect(horaCorta('2026-09-22T15:05:00')).toMatch(/3[:.]05/)
  })

  it('devuelve — si no hay fecha', () => {
    expect(horaCorta(null)).toBe('—')
  })
})
