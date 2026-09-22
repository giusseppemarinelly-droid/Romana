import { useCallback, useEffect, useState } from 'react'
import type { Sesion } from '../types/auth'

// sessionStorage y no localStorage: la sesión muere al cerrar la
// pestaña. El JWT que devuelve el backend sirve para TODA la API
// (incluidas las rutas de escritura), aunque esta web nunca las use --
// cuanto menos viva guardado en el navegador, mejor. Ver Risks en
// tasks/plan.md.
const CLAVE = 'romana.sesion'

export function guardarSesion(sesion: Sesion): void {
  sessionStorage.setItem(CLAVE, JSON.stringify(sesion))
}

export function borrarSesion(): void {
  sessionStorage.removeItem(CLAVE)
}

export function leerSesion(): Sesion | null {
  const crudo = sessionStorage.getItem(CLAVE)
  if (!crudo) return null
  try {
    const sesion = JSON.parse(crudo) as Sesion
    if (sesion.expiraEn > Date.now()) return sesion
  } catch {
    // dato corrupto -- se trata igual que una sesión vencida
  }
  borrarSesion()
  return null
}

export function useSesion() {
  const [sesion, setSesion] = useState<Sesion | null>(leerSesion)

  const iniciar = useCallback((nueva: Sesion) => {
    guardarSesion(nueva)
    setSesion(nueva)
  }, [])

  const cerrar = useCallback(() => {
    borrarSesion()
    setSesion(null)
  }, [])

  // El token dura 12h (JWT_EXPIRE_MINUTES) y un tablero de supervisión
  // puede quedar abierto más que eso -- al vencer, volver al login en
  // vez de quedar mostrando datos viejos con requests que ya fallan.
  useEffect(() => {
    if (!sesion) return
    // setTimeout desborda por encima de ~24.8 días y dispara al instante;
    // se acota por si algún día se sube JWT_EXPIRE_MINUTES.
    const espera = Math.min(Math.max(0, sesion.expiraEn - Date.now()), 2_147_483_647)
    const id = window.setTimeout(cerrar, espera)
    return () => window.clearTimeout(id)
  }, [sesion, cerrar])

  return { sesion, iniciar, cerrar }
}
