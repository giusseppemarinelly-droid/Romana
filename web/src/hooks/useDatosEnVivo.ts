import { useCallback, useEffect, useRef, useState } from 'react'
import { ErrorApi } from '../api/pesadas'
import { useWebSocket } from './useWebSocket'

// Refresca los "hace X min" sin volver a pedir datos. Si además el
// WebSocket está caído, aprovecha y recarga: mejor algo de consulta
// periódica que un tablero viejo sin que se note.
const INTERVALO_REFRESCO_MS = 30_000

/**
 * Datos del backend que se mantienen al día solos: carga inicial,
 * recarga ante cualquier evento del WebSocket, y respaldo por intervalo
 * mientras la conexión esté caída.
 *
 * El WebSocket solo avisa "algo cambió"; los datos siempre se vuelven a
 * pedir por HTTP -- el estado real vive en Postgres (ver
 * backend/ws/manager.py).
 */
export function useDatosEnVivo<T>(
  token: string,
  traer: (token: string) => Promise<T>,
  alExpirarSesion: () => void,
) {
  const [datos, setDatos] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [actualizado, setActualizado] = useState<string | null>(null)
  const [, setTick] = useState(0)

  // En un ref para que pasar una lambda distinta en cada render no
  // dispare una recarga infinita.
  const traerRef = useRef(traer)
  useEffect(() => {
    traerRef.current = traer
  }, [traer])

  const cargar = useCallback(
    async (sigueVigente: () => boolean = () => true) => {
      try {
        const resultado = await traerRef.current(token)
        // Descarta respuestas que llegan tarde, después de que la
        // pantalla se desmontó o de que ya se pidió otra recarga.
        if (!sigueVigente()) return
        setDatos(resultado)
        setActualizado(new Date().toISOString())
        setError(null)
      } catch (e) {
        if (!sigueVigente()) return
        // 401 = el token venció o dejó de valer: volver al login en vez
        // de dejar datos viejos en pantalla con errores en silencio.
        if (e instanceof ErrorApi && e.status === 401) {
          alExpirarSesion()
          return
        }
        setError(e instanceof Error ? e.message : 'No se pudieron cargar los datos.')
      }
    },
    [token, alExpirarSesion],
  )

  const alLlegarEvento = useCallback(() => void cargar(), [cargar])
  const { conectado } = useWebSocket(token, alLlegarEvento)

  useEffect(() => {
    let vigente = true
    // Patrón de carga de datos que documenta React: efecto + bandera
    // para descartar la respuesta si la pantalla ya se fue.
    void cargar(() => vigente)
    return () => {
      vigente = false
    }
  }, [cargar])

  useEffect(() => {
    const id = window.setInterval(() => {
      setTick((t) => t + 1)
      if (!conectado) void cargar()
    }, INTERVALO_REFRESCO_MS)
    return () => window.clearInterval(id)
  }, [conectado, cargar])

  return { datos, error, actualizado, conectado, recargar: () => void cargar() }
}
