import type { Pesada } from '../types/pesada'

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
 * Solo GET: esta web no escribe nada (ver Boundaries en
 * docs/SPEC-web-supervision.md). La única excepción de todo el proyecto
 * es el login, en api/auth.ts.
 */
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

/** Las cinco columnas del tablero, en paralelo. */
export async function obtenerTablero(token: string) {
  const [enPlanta, pendientesAprobacion, rechazadas, aprobadas, completadas] = await Promise.all([
    obtenerEnPlanta(token),
    obtenerPendientesAprobacion(token),
    obtenerRechazadas(token),
    obtenerAprobadasPendientes(token),
    obtenerCompletadas(token),
  ])
  return { enPlanta, pendientesAprobacion, rechazadas, aprobadas, completadas }
}
