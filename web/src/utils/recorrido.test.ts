import { describe, expect, it } from 'vitest'
import { pesada } from '../pruebas'
import type { UsuarioDePesada } from '../types/pesada'
import { armarRecorrido } from './recorrido'

const usuario = (nombre: string): UsuarioDePesada => ({ id: 1, username: nombre, nombre_completo: nombre })

const ENTRADA = '2026-09-24T08:00:00'
const CAPTURA = '2026-09-24T09:00:00'
const DECISION = '2026-09-24T09:30:00'
const SALIDA = '2026-09-24T10:00:00'

function estados(etapas: ReturnType<typeof armarRecorrido>) {
  return etapas.map((e) => [e.clave, e.estado])
}

describe('armarRecorrido', () => {
  it('recién entrada: solo la entrada está hecha, lo demás pendiente', () => {
    const etapas = armarRecorrido(
      pesada({
        estado: 'en_planta',
        fecha_entrada: ENTRADA,
        fecha_captura: null,
        usuario_entrada: usuario('Ana Romana'),
      }),
    )

    expect(estados(etapas)).toEqual([
      ['entrada', 'hecha'],
      ['captura', 'pendiente'],
      ['decision', 'pendiente'],
      ['completado', 'pendiente'],
    ])
    expect(etapas[0].responsable).toBe('Ana Romana')
    expect(etapas[0].datos).toEqual([{ etiqueta: 'Peso de entrada', valor: '10.000 kg' }])
  })

  it('en planta no cuenta una fecha de captura suelta como captura hecha', () => {
    const etapas = armarRecorrido(pesada({ estado: 'en_planta', fecha_captura: CAPTURA }))
    expect(etapas[1].estado).toBe('pendiente')
  })

  it('completada por Costos: las cuatro etapas hechas, con quién y los pesos', () => {
    const etapas = armarRecorrido(
      pesada({
        estado: 'completado',
        fecha_entrada: ENTRADA,
        fecha_captura: CAPTURA,
        fecha_aprobacion: DECISION,
        fecha_salida: SALIDA,
        peso_final: 20_050,
        usuario_salida: usuario('Luis Romana'),
        aprobado_por: usuario('Carla Costos'),
        usuario_completado: usuario('Luis Romana'),
      }),
    )

    expect(etapas.every((e) => e.estado === 'hecha')).toBe(true)
    expect(etapas[1].datos.map((d) => d.etiqueta)).toEqual(['Bruto', 'Tara', 'Neto'])
    expect(etapas[2].titulo).toBe('Aprobada por Costos')
    expect(etapas[2].responsable).toBe('Carla Costos')
    expect(etapas[3].datos).toEqual([{ etiqueta: 'Peso final', valor: '20.050 kg' }])
    expect(etapas[3].fecha).toBe(SALIDA)
  })

  it('aprobada con comentario: la etapa de Costos lo muestra', () => {
    const [, , decision] = armarRecorrido(
      pesada({
        estado: 'aprobado',
        fecha_entrada: ENTRADA,
        fecha_captura: CAPTURA,
        fecha_aprobacion: DECISION,
        aprobado_por: usuario('Carla Costos'),
        comentario_aprobacion: 'La guía venía sin las paletas.',
      }),
    )

    expect(decision.titulo).toBe('Aprobada por Costos')
    expect(decision.nota).toBe('Comentario: La guía venía sin las paletas.')
  })

  it('auto-aprobada: la decisión es "Automática", sin usuario de Costos', () => {
    const [, , decision] = armarRecorrido(
      pesada({
        estado: 'aprobado',
        auto_aprobado: true,
        fecha_captura: CAPTURA,
        fecha_aprobacion: CAPTURA,
      }),
    )
    expect(decision.titulo).toBe('Aprobada automáticamente')
    expect(decision.responsable).toBe('Automática')
    expect(decision.estado).toBe('hecha')
  })

  it('rechazada: muestra el motivo y deja el cierre pendiente', () => {
    const etapas = armarRecorrido(
      pesada({
        estado: 'rechazado',
        fecha_captura: CAPTURA,
        fecha_aprobacion: DECISION,
        motivo_rechazo: 'La guía no coincide',
        aprobado_por: usuario('Carla Costos'),
      }),
    )
    const decision = etapas[2]
    expect(decision.titulo).toBe('Rechazada por Costos')
    expect(decision.punto).toBe('bg-error')
    expect(decision.nota).toContain('La guía no coincide')
    expect(decision.nota).toContain('volver a pesar')
    expect(etapas[3].estado).toBe('pendiente')
  })

  it('re-capturada tras un rechazo: la decisión vuelve a pendiente y avisa, sin inventar el motivo', () => {
    // El backend deja fecha_aprobacion/aprobado_por del rechazo viejo y
    // borra motivo_rechazo al re-capturar.
    const [, captura, decision] = armarRecorrido(
      pesada({
        estado: 'pendiente_aprobacion',
        fecha_aprobacion: DECISION,
        fecha_captura: SALIDA, // posterior al rechazo
        motivo_rechazo: null,
        aprobado_por: usuario('Carla Costos'),
      }),
    )
    expect(captura.estado).toBe('hecha')
    expect(decision.estado).toBe('pendiente')
    expect(decision.fecha).toBeNull()
    expect(decision.nota).toContain('rechazo anterior')
    expect(decision.nota).toContain('Carla Costos')
  })

  it('anulada antes de la decisión: lo que no pasó queda "omitida" y se agrega la anulación', () => {
    const etapas = armarRecorrido(
      pesada({
        estado: 'anulado',
        anulada: true,
        fecha_captura: CAPTURA,
        fecha_aprobacion: null,
        fecha_anulacion: SALIDA,
        motivo_anulacion: 'Camión equivocado',
        anulado_por: usuario('Pedro Supervisor'),
      }),
    )
    expect(estados(etapas)).toEqual([
      ['entrada', 'hecha'],
      ['captura', 'hecha'],
      ['decision', 'omitida'],
      ['completado', 'omitida'],
      ['anulada', 'hecha'],
    ])
    const anulada = etapas[4]
    expect(anulada.responsable).toBe('Pedro Supervisor')
    expect(anulada.fecha).toBe(SALIDA)
    expect(anulada.nota).toBe('Motivo: Camión equivocado')
  })

  it('anulada después de aprobada: conserva la aprobación', () => {
    const [, , decision, completado] = armarRecorrido(
      pesada({
        estado: 'anulado',
        anulada: true,
        fecha_captura: CAPTURA,
        fecha_aprobacion: DECISION,
        aprobado_por: usuario('Carla Costos'),
      }),
    )
    expect(decision.titulo).toBe('Aprobada por Costos')
    expect(decision.estado).toBe('hecha')
    expect(completado.estado).toBe('omitida')
  })

  it('completada sin peso final (pesada vieja): lo dice en vez de mostrar un cero', () => {
    const [, , , completado] = armarRecorrido(
      pesada({ estado: 'completado', fecha_aprobacion: DECISION, fecha_salida: SALIDA, peso_final: null }),
    )
    expect(completado.datos).toEqual([{ etiqueta: 'Peso final', valor: '—' }])
    expect(completado.nota).toContain('Sin peso final')
  })
})
