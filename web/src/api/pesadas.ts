import type { Pesada } from '../types/pesada'
import { puede } from '../utils/permisos'

export class ErrorApi extends Error {
  // Campo declarado aparte y no como propiedad del constructor: el
  // proyecto compila con `erasableSyntaxOnly`, que solo admite sintaxis
  // de tipos que se pueda borrar sin transformar el código.
  readonly status: number

  constructor(mensaje: string, status: number) {
    super(mensaje)
    this.status = status
  }
}

/**
 * Mensaje de error legible: FastAPI manda {"detail": "..."} con el motivo
 * real (ej. "La pesada ya no está pendiente de aprobación").
 */
async function mensajeDeError(respuesta: Response): Promise<string> {
  try {
    const cuerpo = (await respuesta.json()) as { detail?: unknown }
    if (typeof cuerpo.detail === 'string') return cuerpo.detail
  } catch {
    // sin cuerpo JSON: se usa el genérico
  }
  return `El servidor respondió ${respuesta.status}.`
}

export async function getJson<T>(ruta: string, token: string): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(`/api/v1${ruta}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  } catch {
    throw new ErrorApi('No se pudo conectar con el servidor.', 0)
  }

  if (!respuesta.ok) {
    // 401 = token vencido o revocado; quien llama decide (volver al login).
    throw new ErrorApi(`El servidor respondió ${respuesta.status}.`, respuesta.status)
  }
  return (await respuesta.json()) as T
}

/**
 * Escrituras de la web. Hoy son solo las decisiones de Centro de Costos
 * (aprobar / rechazar) -- ver Boundaries en docs/SPEC-web-supervision.md.
 * El backend valida el permiso `centro_costos` en cada una.
 */
export async function postJson<T>(ruta: string, token: string, cuerpo?: unknown): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(`/api/v1${ruta}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        ...(cuerpo === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    })
  } catch {
    throw new ErrorApi('No se pudo conectar con el servidor.', 0)
  }

  if (!respuesta.ok) {
    throw new ErrorApi(await mensajeDeError(respuesta), respuesta.status)
  }
  return (await respuesta.json()) as T
}

export const obtenerEnPlanta = (token: string) => getJson<Pesada[]>('/pesadas/en-planta', token)

export const obtenerPendientesAprobacion = (token: string) =>
  getJson<Pesada[]>('/pesadas/pendientes-aprobacion', token)

export const obtenerAprobadasPendientes = (token: string) =>
  getJson<Pesada[]>('/pesadas/aprobadas-pendientes', token)

/** Completadas es histórico y crece sin límite -- el tablero muestra solo las últimas. */
export const obtenerCompletadas = (token: string, limite = 20) =>
  getJson<Pesada[]>(`/pesadas/completadas?limit=${limite}`, token)

export const obtenerAutoAprobadas = (token: string) =>
  getJson<Pesada[]>('/pesadas/auto-aprobadas', token)

/**
 * Rechazadas por Costos: el camión sigue en planta esperando que Romana
 * vuelva a pesarlo. No tienen listado propio en el backend, así que se
 * piden por el kardex filtrando por estado (permiso `reportes_ver`,
 * niveles 1-2-3).
 */
export const obtenerRechazadas = (token: string, limite = 20) =>
  getJson<Pesada[]>(`/pesadas/kardex/buscar?estado=rechazado&limit=${limite}`, token)

/**
 * Las cinco columnas del tablero, en paralelo. Las rechazadas salen del
 * kardex (reportes_ver): Centro de Costos no tiene ese permiso, así que
 * para ese nivel no se piden -- un 403 ahí tumbaba el tablero entero.
 */
export async function obtenerTablero(token: string, nivel: number) {
  const [enPlanta, pendientesAprobacion, rechazadas, aprobadas, completadas] = await Promise.all([
    obtenerEnPlanta(token),
    obtenerPendientesAprobacion(token),
    puede(nivel, 'reportes_ver') ? obtenerRechazadas(token) : Promise.resolve([]),
    obtenerAprobadasPendientes(token),
    obtenerCompletadas(token),
  ])
  return { enPlanta, pendientesAprobacion, rechazadas, aprobadas, completadas }
}

/** Una pesada completa, con maestros y usuarios de cada etapa. Cualquier usuario logueado. */
export const obtenerPesada = (token: string, id: number) =>
  getJson<Pesada>(`/pesadas/${id}`, token)

/** Tope de filas del historial: el mismo default del backend (get_kardex). */
export const LIMITE_KARDEX = 500

export interface FiltrosKardex {
  /** Fechas locales YYYY-MM-DD, las dos inclusive. Vacías = sin límite. */
  desde: string
  hasta: string
  /** Estado del backend (en_planta, anulado...) o '' para todos. */
  estado: string
}

/**
 * Historial de pesadas por fecha de ENTRADA (así filtra get_kardex), las
 * más nuevas primero. Permiso `reportes_ver` (niveles 1-2-3).
 *
 * El backend compara `fecha_entrada` (hora local del servidor, sin zona)
 * con `>=` y `<=`: "hasta" se manda como el último instante del día para
 * que el día entero quede adentro, incluidos los microsegundos que guarda
 * datetime.now() -- con T23:59:59 a secas se perdería una entrada a las
 * 23:59:59.4.
 */
export function buscarKardex(token: string, filtros: FiltrosKardex, limite = LIMITE_KARDEX) {
  const parametros = new URLSearchParams()
  if (filtros.desde) parametros.set('fecha_inicio', `${filtros.desde}T00:00:00`)
  if (filtros.hasta) parametros.set('fecha_fin', `${filtros.hasta}T23:59:59.999999`)
  if (filtros.estado) parametros.set('estado', filtros.estado)
  parametros.set('limit', String(limite))
  return getJson<Pesada[]>(`/pesadas/kardex/buscar?${parametros.toString()}`, token)
}

/**
 * El ticket PDF que genera el backend (el mismo formato de planilla que
 * imprime la Romana). Pide `reportes_ver` y el token va en el header, así
 * que no sirve un <a href> directo: se baja como Blob.
 */
export async function obtenerTicketPdf(token: string, id: number): Promise<Blob> {
  let respuesta: Response
  try {
    respuesta = await fetch(`/api/v1/reportes/ticket/${id}.pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  } catch {
    throw new ErrorApi('No se pudo conectar con el servidor.', 0)
  }
  if (!respuesta.ok) throw new ErrorApi(await mensajeDeError(respuesta), respuesta.status)
  // Con tipo explícito: sin él, el visor del navegador no sabe que es un PDF.
  return new Blob([await respuesta.arrayBuffer()], { type: 'application/pdf' })
}
