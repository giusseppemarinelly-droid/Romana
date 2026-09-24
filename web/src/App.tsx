import { useState } from 'react'
import { useSesion } from './hooks/useSesion'
import { useTema } from './hooks/useTema'
import { Costos } from './pages/Costos'
import { Dashboard } from './pages/Dashboard'
import { Estadisticas } from './pages/Estadisticas'
import { Login } from './pages/Login'
import { Maestros } from './pages/Maestros'
import { Tickets } from './pages/Tickets'
import { paginasPara, type Pagina } from './utils/paginas'

const PANTALLAS = {
  tablero: Dashboard,
  tickets: Tickets,
  estadisticas: Estadisticas,
  costos: Costos,
  maestros: Maestros,
}

export function App() {
  const { sesion, iniciar, cerrar } = useSesion()
  const [pagina, setPagina] = useState<Pagina>('tablero')
  const { tema, alternar } = useTema()

  if (!sesion) return <Login onIngreso={iniciar} />

  // Si la sesión cambió a un nivel sin acceso a la pantalla abierta
  // (ej. entra Centro de Costos después de un Supervisor en Maestros),
  // se vuelve al tablero en vez de mostrar una pantalla que da 403.
  const permitida = paginasPara(sesion.usuario.nivel).includes(pagina) ? pagina : 'tablero'
  const Pantalla = PANTALLAS[permitida]
  return (
    <Pantalla
      sesion={sesion}
      onCerrarSesion={cerrar}
      pagina={permitida}
      onCambiarPagina={setPagina}
      tema={tema}
      onAlternarTema={alternar}
    />
  )
}
