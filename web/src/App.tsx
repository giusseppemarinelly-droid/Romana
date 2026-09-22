import { useState } from 'react'
import type { Pagina } from './components/Navegacion'
import { useSesion } from './hooks/useSesion'
import { useTema } from './hooks/useTema'
import { Costos } from './pages/Costos'
import { Dashboard } from './pages/Dashboard'
import { Estadisticas } from './pages/Estadisticas'
import { Login } from './pages/Login'

const PANTALLAS = { tablero: Dashboard, estadisticas: Estadisticas, costos: Costos }

export function App() {
  const { sesion, iniciar, cerrar } = useSesion()
  const [pagina, setPagina] = useState<Pagina>('tablero')
  const { tema, alternar } = useTema()

  if (!sesion) return <Login onIngreso={iniciar} />

  const Pantalla = PANTALLAS[pagina]
  return (
    <Pantalla
      sesion={sesion}
      onCerrarSesion={cerrar}
      pagina={pagina}
      onCambiarPagina={setPagina}
      tema={tema}
      onAlternarTema={alternar}
    />
  )
}
