import { useEffect, useState } from 'react'
import type { Tema } from '../tema'

const CLAVE = 'romana.tema'

// localStorage puede no estar (ventana privada, sitio bloqueado): sin él
// la web anda igual, solo que no recuerda la elección.
export function leerTemaGuardado(): Tema {
  try {
    return localStorage.getItem(CLAVE) === 'oscuro' ? 'oscuro' : 'claro'
  } catch {
    return 'claro'
  }
}

export function aplicarTema(tema: Tema) {
  document.documentElement.dataset.tema = tema
}

/** Tema claro por defecto (la paleta de escritorio); el oscuro es opcional y se recuerda. */
export function useTema() {
  const [tema, setTema] = useState<Tema>(leerTemaGuardado)

  useEffect(() => {
    aplicarTema(tema)
    try {
      localStorage.setItem(CLAVE, tema)
    } catch {
      // sin almacenamiento: se usa el tema solo por esta visita
    }
  }, [tema])

  const alternar = () => setTema((t) => (t === 'claro' ? 'oscuro' : 'claro'))
  return { tema, alternar }
}
