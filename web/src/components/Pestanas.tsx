import { useRef, type KeyboardEvent } from 'react'
import { idsPestana } from '../utils/pestanas'

export interface Pestana<C extends string> {
  clave: C
  etiqueta: string
}

/**
 * Fila de pestañas accesible (patrón "tabs" de WAI-ARIA): solo la activa
 * entra en el orden de Tab, y entre ellas se mueve con las flechas
 * izquierda/derecha (y Inicio/Fin). Activación automática: mover el foco
 * ya cambia de pestaña, que es lo esperable cuando cambiar es barato.
 *
 * Los paneles los dibuja quien la usa, con `idsPestana` (utils/pestanas.ts) para los ids.
 * Estilo del activo igual al del filtro activo de FiltrosEstado.
 */
export function Pestanas<C extends string>({
  base,
  etiqueta,
  pestanas,
  actual,
  onCambiar,
}: {
  base: string
  /** Nombre del grupo para lectores de pantalla. */
  etiqueta: string
  pestanas: Pestana<C>[]
  actual: C
  onCambiar: (clave: C) => void
}) {
  const botones = useRef(new Map<C, HTMLButtonElement>())

  function alPresionarTecla(e: KeyboardEvent<HTMLButtonElement>) {
    const i = pestanas.findIndex((p) => p.clave === actual)
    const destino: Record<string, number> = {
      ArrowRight: (i + 1) % pestanas.length,
      ArrowLeft: (i - 1 + pestanas.length) % pestanas.length,
      Home: 0,
      End: pestanas.length - 1,
    }
    if (!(e.key in destino)) return
    e.preventDefault()
    const siguiente = pestanas[destino[e.key]].clave
    onCambiar(siguiente)
    botones.current.get(siguiente)?.focus()
  }

  return (
    <div role="tablist" aria-label={etiqueta} className="flex flex-wrap gap-1">
      {pestanas.map(({ clave, etiqueta: texto }) => {
        const activa = clave === actual
        const ids = idsPestana(base, clave)
        return (
          <button
            key={clave}
            ref={(el) => {
              if (el) botones.current.set(clave, el)
              else botones.current.delete(clave)
            }}
            type="button"
            role="tab"
            id={ids.pestana}
            aria-selected={activa}
            aria-controls={ids.panel}
            tabIndex={activa ? 0 : -1}
            onClick={() => onCambiar(clave)}
            onKeyDown={alPresionarTecla}
            className={`flex h-5 items-center rounded-control border px-2 transition-colors ${
              activa
                ? 'border-acento bg-acento text-blanco hover:bg-acento-hover'
                : 'border-borde text-muted hover:bg-borde hover:text-texto'
            }`}
          >
            {texto}
          </button>
        )
      })}
    </div>
  )
}
