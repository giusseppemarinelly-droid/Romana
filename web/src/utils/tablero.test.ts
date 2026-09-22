import { describe, expect, it } from 'vitest'
import type { Pesada } from '../types/pesada'
import { aplanarTablero, type DatosTablero } from './tablero'

const AHORA = new Date('2026-09-22T15:00:00')

function pesada(ticket: string, campos: Partial<Pesada> = {}): Pesada {
  return { id: Number(ticket.slice(-1)), numero_ticket: ticket, ...campos } as unknown as Pesada
}

function hace(minutos: number): string {
  return new Date(AHORA.getTime() - minutos * 60_000).toISOString()
}

function vacio(): DatosTablero {
  return { enPlanta: [], pendientesAprobacion: [], rechazadas: [], aprobadas: [], completadas: [] }
}

describe('aplanarTablero', () => {
  it('ordena primero lo que lleva más tiempo trabado, sin importar el estado', () => {
    const filas = aplanarTablero(
      {
        ...vacio(),
        enPlanta: [pesada('TK-1', { fecha_entrada: hace(30) })],
        pendientesAprobacion: [pesada('TK-2', { fecha_captura: hace(200) })],
        aprobadas: [pesada('TK-3', { fecha_aprobacion: hace(90) })],
      },
      AHORA,
    )

    expect(filas.map((f) => f.pesada.numero_ticket)).toEqual(['TK-2', 'TK-3', 'TK-1'])
  })

  it('manda las completadas al final: no están esperando nada', () => {
    const filas = aplanarTablero(
      {
        ...vacio(),
        enPlanta: [pesada('TK-1', { fecha_entrada: hace(5) })],
        completadas: [pesada('TK-9', { fecha_salida: hace(600) })],
      },
      AHORA,
    )

    expect(filas.map((f) => f.pesada.numero_ticket)).toEqual(['TK-1', 'TK-9'])
    expect(filas[1].minutos).toBeNull()
  })

  it('entre completadas, primero la más reciente', () => {
    const filas = aplanarTablero(
      {
        ...vacio(),
        completadas: [
          pesada('TK-8', { fecha_salida: hace(300) }),
          pesada('TK-9', { fecha_salida: hace(30) }),
        ],
      },
      AHORA,
    )

    expect(filas.map((f) => f.pesada.numero_ticket)).toEqual(['TK-9', 'TK-8'])
  })

  it('marca las demoradas según el umbral de su estado', () => {
    const filas = aplanarTablero(
      {
        ...vacio(),
        // 2 h en planta todavía no es demora (umbral 4 h), pero 2 h
        // esperando a Costos sí lo es (umbral 1 h).
        enPlanta: [pesada('TK-1', { fecha_entrada: hace(120) })],
        pendientesAprobacion: [pesada('TK-2', { fecha_captura: hace(120) })],
      },
      AHORA,
    )

    expect(filas.find((f) => f.pesada.numero_ticket === 'TK-1')!.demorada).toBe(false)
    expect(filas.find((f) => f.pesada.numero_ticket === 'TK-2')!.demorada).toBe(true)
  })

  it('no rompe con pesadas viejas sin la fecha de referencia', () => {
    const filas = aplanarTablero(
      { ...vacio(), enPlanta: [pesada('TK-1', { fecha_entrada: null })] },
      AHORA,
    )

    expect(filas).toHaveLength(1)
    expect(filas[0].minutos).toBeNull()
    expect(filas[0].demorada).toBe(false)
  })

  it('cada fila sabe de qué estado viene', () => {
    const filas = aplanarTablero(
      { ...vacio(), rechazadas: [pesada('TK-4', { fecha_captura: hace(10) })] },
      AHORA,
    )

    expect(filas[0].estado).toBe('rechazadas')
  })
})
