import type { ReactNode } from 'react'
import type { Tema } from '../tema'
import type { Sesion } from '../types/auth'
import { BarraLateral } from './BarraLateral'
import type { Pagina } from './Navegacion'
import { Punto } from './Punto'

/** Lo que App le pasa a cada pantalla. */
export interface PropsPagina {
  sesion: Sesion
  onCerrarSesion: () => void
  pagina: Pagina
  onCambiarPagina: (pagina: Pagina) => void
  tema: Tema
  onAlternarTema: () => void
}

/**
 * Esqueleto común de las pantallas: sidebar, título, aviso de error y
 * contenido. El estado de conexión lo trae cada pantalla porque cada una
 * mantiene sus propios datos en vivo.
 */
export function Marco({
  titulo,
  descripcion,
  conectado,
  actualizado,
  error,
  onReintentar,
  children,
  ...props
}: PropsPagina & {
  titulo: string
  descripcion: string
  conectado: boolean
  actualizado: string | null
  error: string | null
  onReintentar: () => void
  children: ReactNode
}) {
  return (
    <div className="min-h-screen">
      <BarraLateral {...props} conectado={conectado} actualizado={actualizado} />

      <main className="flex flex-col gap-4 p-3 md:pl-34 md:pr-4 md:py-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-titulo font-bold">{titulo}</h1>
          <p className="text-muted">{descripcion}</p>
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-center justify-between gap-2 rounded-card border border-error bg-card px-3 py-2"
          >
            <span className="flex items-center gap-1">
              <Punto color="bg-error" />
              {error}
            </span>
            <button
              type="button"
              onClick={onReintentar}
              className="h-5 shrink-0 rounded-control border border-borde px-2 transition-colors hover:bg-borde"
            >
              Reintentar
            </button>
          </div>
        )}

        {children}
      </main>
    </div>
  )
}
