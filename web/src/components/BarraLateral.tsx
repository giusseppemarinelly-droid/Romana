import type { Tema } from '../tema'
import type { Sesion } from '../types/auth'
import { EstadoConexion } from './EstadoConexion'
import { IconoBalanza } from './IconoBalanza'
import { Navegacion, type Pagina } from './Navegacion'

const BOTON =
  'h-5 rounded-control border border-lateral-borde px-2 transition-colors hover:bg-lateral-hover'

/**
 * Sidebar fija de 240px con las secciones, la conexión (siempre a la
 * vista) y la sesión. En pantallas angostas deja de estar fija y queda
 * arriba del contenido.
 */
export function BarraLateral({
  sesion,
  onCerrarSesion,
  pagina,
  onCambiarPagina,
  conectado,
  actualizado,
  tema,
  onAlternarTema,
}: {
  sesion: Sesion
  onCerrarSesion: () => void
  pagina: Pagina
  onCambiarPagina: (pagina: Pagina) => void
  conectado: boolean
  actualizado: string | null
  tema: Tema
  onAlternarTema: () => void
}) {
  return (
    <aside className="flex flex-col gap-4 border-b border-lateral-borde bg-lateral p-3 text-lateral-texto md:fixed md:inset-y-0 md:left-0 md:w-30 md:border-r md:border-b-0">
      <div className="flex items-center gap-2">
        <IconoBalanza className="size-4" />
        <div>
          <p className="text-subtitulo font-bold">Romana</p>
          <p className="text-lateral-muted">Supervisión</p>
        </div>
      </div>

      <Navegacion actual={pagina} nivel={sesion.usuario.nivel} onCambiar={onCambiarPagina} />

      <div className="flex flex-col gap-2 border-t border-lateral-borde pt-3 md:mt-auto">
        <EstadoConexion conectado={conectado} actualizado={actualizado} />
        <div>
          <p className="font-semibold">{sesion.usuario.nombre_completo}</p>
          <p className="text-lateral-muted">{sesion.nivelNombre}</p>
        </div>
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={onAlternarTema}
            aria-pressed={tema === 'oscuro'}
            className={BOTON}
          >
            {tema === 'oscuro' ? 'Modo claro' : 'Modo oscuro'}
          </button>
          <button type="button" onClick={onCerrarSesion} className={BOTON}>
            Cerrar sesión
          </button>
        </div>
      </div>
    </aside>
  )
}
