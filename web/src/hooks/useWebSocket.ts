import { useEffect, useRef, useState } from 'react'

export interface EventoPesada {
  tipo: string
  pesada_id?: number
}

const ESPERA_INICIAL_MS = 1_000
const ESPERA_MAXIMA_MS = 30_000

/**
 * Conexión al broadcast del backend (`/ws/pesadas`), con reconexión de
 * espera creciente -- mismo criterio que client/ws_client.py en la app
 * de escritorio (1s → 30s tope).
 *
 * El WebSocket es solo un aviso de "algo cambió", NO la fuente de
 * verdad: quien lo usa vuelve a pedir los datos por HTTP. Si se pierde
 * un evento por estar desconectado, la próxima recarga lo corrige.
 *
 * Ojo: si el token está vencido, el backend rechaza el handshake y el
 * navegador ve un cierre genérico (1006), indistinguible de un corte de
 * red -- por eso acá se reintenta siempre, y de la sesión vencida se
 * encarga useSesion, que cierra sesión sola al llegar el vencimiento.
 */
export function useWebSocket(token: string, alRecibirEvento: (evento: EventoPesada) => void) {
  const [conectado, setConectado] = useState(false)
  // En refs y no en estado: cambian seguido y no deben provocar
  // re-renders ni reconexiones.
  const callbackRef = useRef(alRecibirEvento)
  const esperaRef = useRef(ESPERA_INICIAL_MS)

  useEffect(() => {
    callbackRef.current = alRecibirEvento
  }, [alRecibirEvento])

  useEffect(() => {
    if (!token) return

    let socket: WebSocket | null = null
    let timer: number | undefined
    let desmontado = false

    const conectar = () => {
      if (desmontado) return

      const protocolo = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(
        `${protocolo}//${window.location.host}/ws/pesadas?token=${encodeURIComponent(token)}`,
      )

      socket.onopen = () => {
        esperaRef.current = ESPERA_INICIAL_MS
        setConectado(true)
      }

      socket.onmessage = (e) => {
        try {
          callbackRef.current(JSON.parse(e.data as string) as EventoPesada)
        } catch {
          // mensaje no-JSON: se ignora, no vale tumbar la conexión por esto
        }
      }

      socket.onclose = () => {
        setConectado(false)
        if (desmontado) return
        timer = window.setTimeout(conectar, esperaRef.current)
        esperaRef.current = Math.min(esperaRef.current * 2, ESPERA_MAXIMA_MS)
      }

      // onerror siempre viene seguido de onclose, que es donde se
      // reintenta -- acá solo se evita el error no manejado en consola.
      socket.onerror = () => {}
    }

    conectar()

    return () => {
      desmontado = true
      window.clearTimeout(timer)
      socket?.close()
    }
  }, [token])

  return { conectado }
}
