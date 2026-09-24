import type { Pesada, UsuarioDePesada } from '../types/pesada'
import { formatearKg } from './pesadas'

// El recorrido de una pesada se RECONSTRUYE con las fechas y los usuarios
// que guarda cada etapa en la propia fila de `pesadas`: el backend no
// tiene una tabla de historial/auditoría. Consecuencia que hay que decir
// en voz alta en vez de disimular: si Costos rechazó y la Romana volvió a
// pesar, capturar_peso_salida() pisa la captura anterior (pesos, fecha,
// usuario) y borra el motivo del rechazo -- de ese ida y vuelta solo
// queda lo último. Acá no se inventan eventos que la base no tiene.

export type EstadoEtapa = 'hecha' | 'pendiente' | 'omitida'

export interface DatoEtapa {
  etiqueta: string
  valor: string
}

export interface Etapa {
  clave: 'entrada' | 'captura' | 'decision' | 'completado' | 'anulada'
  titulo: string
  estado: EstadoEtapa
  fecha: string | null
  /** Quién la hizo: nombre del usuario, "Automática" o null si no quedó registrado. */
  responsable: string | null
  datos: DatoEtapa[]
  /** Aclaración corta (motivo de rechazo, qué falta, qué no se conserva). */
  nota: string | null
  /** Clase del punto (tokens de index.css). */
  punto: string
}

export const AVISO_HISTORIAL =
  'Se reconstruye con las fechas de cada etapa: si hubo un rechazo y se volvió a pesar, solo queda la última captura.'

const PUNTO_PENDIENTE = 'bg-borde'

function conKg(kilos: number | null | undefined): string {
  const texto = formatearKg(kilos ?? null)
  return texto === '—' ? texto : `${texto} kg`
}

function nombre(usuario: UsuarioDePesada | null | undefined): string | null {
  return usuario?.nombre_completo ?? null
}

function antes(a: string, b: string): boolean {
  return new Date(a).getTime() < new Date(b).getTime()
}

/**
 * Etapas de la pesada, en orden: Entrada → Pre-pesaje → Decisión de
 * Costos → Peso final y salida (→ Anulada, solo si lo está). Las que
 * todavía no ocurrieron quedan "pendiente"; en una anulada, las que ya no
 * van a ocurrir quedan "omitida".
 *
 * El estado actual manda sobre las fechas: después de un rechazo y una
 * nueva captura, `fecha_aprobacion` y `aprobado_por` siguen con los datos
 * del rechazo (el backend no los limpia), así que "tiene fecha" no
 * alcanza para decir que la decisión vigente ya se tomó.
 */
export function armarRecorrido(p: Pesada): Etapa[] {
  const anulada = p.estado === 'anulado' || p.anulada === true
  const faltante: EstadoEtapa = anulada ? 'omitida' : 'pendiente'

  // --- 1. Entrada: primer peso, se escribe una sola vez (peso_entrada). ---
  const entrada: Etapa = {
    clave: 'entrada',
    titulo: 'Entrada',
    estado: p.fecha_entrada ? 'hecha' : faltante,
    fecha: p.fecha_entrada,
    responsable: nombre(p.usuario_entrada),
    datos: [{ etiqueta: 'Peso de entrada', valor: conKg(p.peso_entrada) }],
    nota: null,
    punto: p.fecha_entrada ? 'bg-exito' : PUNTO_PENDIENTE,
  }

  // --- 2. Pre-pesaje: segundo peso, de él salen bruto/tara/neto. ---
  // En "en_planta" todavía no se capturó nada, aunque viniera una fecha.
  const capturada = p.fecha_captura !== null && p.estado !== 'en_planta'
  const captura: Etapa = {
    clave: 'captura',
    titulo: 'Pre-pesaje',
    estado: capturada ? 'hecha' : faltante,
    fecha: capturada ? p.fecha_captura : null,
    responsable: capturada ? nombre(p.usuario_salida) : null,
    datos: capturada
      ? [
          { etiqueta: 'Bruto', valor: conKg(p.peso_bruto) },
          { etiqueta: 'Tara', valor: conKg(p.peso_tara) },
          { etiqueta: 'Neto', valor: conKg(p.peso_neto) },
        ]
      : [],
    nota: null,
    punto: capturada ? 'bg-exito' : PUNTO_PENDIENTE,
  }

  // --- 3. Decisión de Costos (o aprobación automática). ---
  const decision = armarDecision(p, capturada, anulada, faltante)

  // --- 4. Peso final y salida: el tercer pesaje, cierra la pesada. ---
  const completada = p.estado === 'completado'
  const completado: Etapa = {
    clave: 'completado',
    titulo: 'Peso final y salida',
    estado: completada ? 'hecha' : faltante,
    fecha: completada ? p.fecha_salida : null,
    responsable: completada ? nombre(p.usuario_completado) : null,
    datos: completada ? [{ etiqueta: 'Peso final', valor: conKg(p.peso_final) }] : [],
    // Las completadas antes de que existiera el tercer pesaje no lo tienen.
    nota: completada && p.peso_final == null ? 'Sin peso final registrado (pesada anterior a ese campo).' : null,
    punto: completada ? 'bg-exito' : PUNTO_PENDIENTE,
  }

  const etapas = [entrada, captura, decision, completado]

  if (anulada) {
    etapas.push({
      clave: 'anulada',
      titulo: 'Anulada',
      estado: 'hecha',
      fecha: p.fecha_anulacion ?? null,
      responsable: nombre(p.anulado_por),
      datos: [],
      nota: p.motivo_anulacion ? `Motivo: ${p.motivo_anulacion}` : null,
      punto: 'bg-error',
    })
  }

  return etapas
}

function armarDecision(p: Pesada, capturada: boolean, anulada: boolean, faltante: EstadoEtapa): Etapa {
  const base = {
    clave: 'decision' as const,
    titulo: 'Decisión de Costos',
    fecha: null,
    responsable: null,
    datos: [],
    nota: null,
    punto: PUNTO_PENDIENTE,
  }

  // Una decisión es la vigente solo si es posterior a la última captura:
  // si es anterior, es la de un rechazo viejo que la nueva captura dejó
  // atrás (capturar_peso_salida no limpia fecha_aprobacion/aprobado_por).
  const vigente =
    capturada &&
    p.fecha_aprobacion !== null &&
    (p.fecha_captura === null || !antes(p.fecha_aprobacion, p.fecha_captura))
  const rechazoViejo =
    capturada &&
    p.fecha_aprobacion !== null &&
    p.fecha_captura !== null &&
    antes(p.fecha_aprobacion, p.fecha_captura)

  // En rechazado/aprobado/completado la decisión ya se tomó sí o sí (aunque
  // una pesada vieja no tenga la fecha). En una anulada depende de si
  // llegó a haber una decisión vigente antes de anularla.
  const decidida =
    ['rechazado', 'aprobado', 'completado'].includes(p.estado) || (anulada && vigente)
  // motivo_rechazo solo sobrevive mientras la pesada sigue rechazada (la
  // nueva captura lo borra), así que en una anulada dice qué fue lo último.
  const rechazada = p.estado === 'rechazado' || (anulada && !!p.motivo_rechazo)

  if (decidida && rechazada) {
    return {
      ...base,
      titulo: 'Rechazada por Costos',
      estado: 'hecha',
      fecha: p.fecha_aprobacion,
      responsable: nombre(p.aprobado_por),
      nota: [
        p.motivo_rechazo ? `Motivo: ${p.motivo_rechazo}` : 'Sin motivo registrado.',
        p.estado === 'rechazado' ? 'La Romana tiene que volver a pesar el camión.' : null,
      ]
        .filter(Boolean)
        .join(' '),
      punto: 'bg-error',
    }
  }

  if (decidida) {
    return {
      ...base,
      titulo: p.auto_aprobado ? 'Aprobada automáticamente' : 'Aprobada por Costos',
      estado: 'hecha',
      fecha: p.fecha_aprobacion,
      responsable: p.auto_aprobado ? 'Automática' : nombre(p.aprobado_por),
      nota: p.auto_aprobado
        ? 'La diferencia con la guía quedó dentro de la tolerancia.'
        : p.comentario_aprobacion
          ? `Comentario: ${p.comentario_aprobacion}`
          : null,
      punto: 'bg-exito',
    }
  }

  // Todavía sin decisión (o anulada antes de que la hubiera). Si quedó el
  // rastro de un rechazo anterior, se dice, con lo poco que se conserva.
  return {
    ...base,
    estado: faltante,
    nota: rechazoViejo
      ? `Tuvo un rechazo anterior${nombre(p.aprobado_por) ? ` de ${nombre(p.aprobado_por)}` : ''} y se volvió a pesar; el motivo no se conserva.`
      : null,
  }
}
