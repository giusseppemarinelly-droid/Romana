import { useCallback, useEffect, useRef, useState } from 'react'
import { obtenerCatalogo } from '../api/maestros'
import { ErrorApi } from '../api/pesadas'
import type { Catalogos, ClaveCatalogo } from '../types/maestros'
import { useWebSocket } from './useWebSocket'

type PorCatalogo<T> = Partial<Record<ClaveCatalogo, T>>

// El WebSocket del backend solo avisa de pesadas (backend/routers/
// pesadas.py): los maestros no emiten eventos. Se conecta igual para que
// el indicador del sidebar diga la verdad sobre el servidor, pero sus
// eventos no disparan recargas -- recargar el catálogo de vehículos cada
// vez que un camión se pesa sería trabajo tirado.
const ignorarEvento = () => {}

/**
 * Catálogos de la pantalla Maestros, pedidos de a uno y recién cuando se
 * abre su pestaña. Una vez traído, cada catálogo queda en memoria:
 * volver a una pestaña ya vista no pide nada (cambian muy de vez en
 * cuando y hay "Reintentar"/F5 si hace falta).
 *
 * Es el equivalente de useDatosEnVivo para datos que no viven al ritmo
 * del WebSocket: misma forma de devolver datos/error/actualizado/
 * conectado, y mismo criterio ante un 401 (volver al login).
 */
export function useCatalogo<C extends ClaveCatalogo>(
  token: string,
  clave: C,
  alExpirarSesion: () => void,
) {
  const [datos, setDatos] = useState<PorCatalogo<Catalogos[ClaveCatalogo]>>({})
  const [errores, setErrores] = useState<PorCatalogo<string>>({})
  const [actualizados, setActualizados] = useState<PorCatalogo<string>>({})

  // En un ref y no en estado: se consulta dentro del efecto sin volverlo
  // a disparar, y sobrevive al doble montaje de StrictMode (así en
  // desarrollo tampoco se pide dos veces).
  const pedidos = useRef(new Set<ClaveCatalogo>())

  const cargar = useCallback(
    async (c: ClaveCatalogo) => {
      try {
        const resultado = await obtenerCatalogo(c, token)
        // Cada respuesta se guarda en su propio casillero: si llega tarde,
        // después de haber cambiado de pestaña, no pisa a la que se ve.
        setDatos((d) => ({ ...d, [c]: resultado }))
        setActualizados((a) => ({ ...a, [c]: new Date().toISOString() }))
        setErrores((er) => {
          const resto = { ...er }
          delete resto[c]
          return resto
        })
      } catch (e) {
        // 401 = token vencido o revocado: al login, no datos viejos.
        if (e instanceof ErrorApi && e.status === 401) {
          alExpirarSesion()
          return
        }
        const mensaje = e instanceof Error ? e.message : 'No se pudo cargar el catálogo.'
        setErrores((er) => ({ ...er, [c]: mensaje }))
      }
    },
    [token, alExpirarSesion],
  )

  useEffect(() => {
    if (pedidos.current.has(clave)) return
    pedidos.current.add(clave)
    void cargar(clave)
  }, [clave, cargar])

  const { conectado } = useWebSocket(token, ignorarEvento)

  return {
    datos: (datos[clave] as Catalogos[C] | undefined) ?? null,
    error: errores[clave] ?? null,
    actualizado: actualizados[clave] ?? null,
    conectado,
    recargar: () => void cargar(clave),
  }
}
