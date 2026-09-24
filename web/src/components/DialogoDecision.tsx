import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { MOTIVO_MINIMO } from '../api/costos'
import type { Pesada } from '../types/pesada'
import { diferenciaConGuia, formatearKg } from '../utils/pesadas'
import { Punto } from './Punto'

export type Decision = 'aprobar' | 'rechazar'

const TEXTOS: Record<Decision, { titulo: string; consecuencia: string; confirmar: string }> = {
  // Mismos avisos que la estación de escritorio
  // (gui/centro_costos/centro_costos_view.py → _aprobar / _rechazar).
  aprobar: {
    titulo: 'Aprobar',
    consecuencia: 'Al aprobar, la Romana podrá completar los datos finales y autorizar la salida.',
    confirmar: 'Aprobar',
  },
  rechazar: {
    titulo: 'Rechazar',
    consecuencia: 'Al rechazar, la Romana deberá volver a capturar el peso del camión.',
    confirmar: 'Rechazar',
  },
}

const ENFOCABLES = 'button:not([disabled]), textarea:not([disabled]), input:not([disabled])'

function conKg(kilos: number | null) {
  const texto = formatearKg(kilos)
  return texto === '—' ? texto : `${texto} kg`
}

/**
 * Confirmación de una decisión de Centro de Costos, con el resumen que
 * hace falta para decidir (el mismo que muestra el panel de detalle de
 * la estación de escritorio).
 *
 * Modal propio en vez de <dialog>.showModal(): jsdom (los tests) no lo
 * implementa, y armarlo a mano es poco -- overlay, foco atrapado,
 * Escape y devolver el foco al botón que lo abrió.
 *
 * `onConfirmar` hace el POST. Si lanza, el mensaje se muestra acá
 * adentro y el diálogo queda abierto (típico: otro usuario ya decidió);
 * si sale bien, quien lo abrió lo cierra.
 */
export function DialogoDecision({
  pesada,
  decision,
  onConfirmar,
  onCerrar,
}: {
  pesada: Pesada
  decision: Decision
  onConfirmar: (motivo: string) => Promise<void>
  onCerrar: () => void
}) {
  const textos = TEXTOS[decision]
  const idTitulo = useId()
  const idDescripcion = useId()
  const idAyudaMotivo = useId()

  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Además del estado: dos clics seguidos llegan antes de que React
  // vuelva a pintar el botón deshabilitado, y el segundo mandaría otro
  // POST. El ref corta en seco.
  const enviandoRef = useRef(false)

  const panel = useRef<HTMLDivElement>(null)
  const campoMotivo = useRef<HTMLTextAreaElement>(null)
  const botonCancelar = useRef<HTMLButtonElement>(null)

  // Se captura al renderizar (antes de mover el foco adentro): es el
  // botón que abrió el diálogo, al que vuelve el foco al cerrarlo.
  const [quienAbrio] = useState(() => document.activeElement as HTMLElement | null)

  useEffect(() => {
    // El foco va directo al campo de texto (motivo o comentario), que es
    // lo primero que se escribe. Tampoco ahí un Enter de más decide nada
    // por error: en un textarea Enter es un salto de línea.
    const destino = campoMotivo.current ?? botonCancelar.current
    destino?.focus()
    return () => quienAbrio?.focus()
  }, [quienAbrio])

  // Escape cierra, salvo mientras se envía: cerrar ahí dejaría el POST en
  // vuelo sin nadie que muestre si salió bien o mal.
  useEffect(() => {
    function alTeclear(e: globalThis.KeyboardEvent) {
      if (e.key === 'Escape' && !enviandoRef.current) onCerrar()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [onCerrar])

  // Tab y Shift+Tab dan la vuelta dentro del diálogo en vez de irse a la
  // página de atrás (que el overlay tapa pero el teclado seguiría viendo).
  function atraparFoco(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== 'Tab' || !panel.current) return
    const enfocables = [...panel.current.querySelectorAll<HTMLElement>(ENFOCABLES)]
    if (enfocables.length === 0) return
    const primero = enfocables[0]
    const ultimo = enfocables[enfocables.length - 1]
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault()
      ultimo.focus()
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault()
      primero.focus()
    }
  }

  const motivoValido = motivo.trim().length >= MOTIVO_MINIMO
  const puedeConfirmar = !enviando && (decision === 'aprobar' || motivoValido)

  async function confirmar() {
    if (enviandoRef.current || !puedeConfirmar) return
    enviandoRef.current = true
    setEnviando(true)
    setError(null)
    try {
      await onConfirmar(motivo.trim())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo registrar la decisión.')
    } finally {
      enviandoRef.current = false
      setEnviando(false)
    }
  }

  const diferencia = diferenciaConGuia(pesada)
  const resumen: [string, ReactNode][] = [
    ['Ticket', pesada.numero_ticket],
    ['Placa', pesada.vehiculo?.placa ?? '—'],
    ['Producto', pesada.producto?.nombre ?? pesada.empresa_cliente_proveedor ?? '—'],
    ['Neto', conKg(pesada.peso_neto)],
    ['Peso guía', conKg(pesada.peso_guia)],
    [
      'Diferencia c/ guía',
      diferencia === null ? (
        '—'
      ) : (
        <span className="inline-flex items-center gap-1">
          <Punto color={diferencia >= 10 ? 'bg-error' : 'bg-advertencia'} />
          {diferencia.toFixed(2)} %
        </span>
      ),
    ],
  ]

  return (
    // Clic afuera NO cierra a propósito: en un rechazo borraría el motivo
    // ya escrito por un clic distraído. Para salir: Cancelar o Escape.
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-fondo/80 p-2">
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={idDescripcion}
        onKeyDown={atraparFoco}
        className="flex max-h-full w-full max-w-60 flex-col gap-3 overflow-y-auto rounded-card border border-borde bg-card p-3"
      >
        <div className="flex flex-col gap-1">
          <h2 id={idTitulo} className="text-subtitulo font-semibold">
            {textos.titulo} {pesada.numero_ticket}
          </h2>
          <p id={idDescripcion} className="text-muted">
            {textos.consecuencia}
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-x-2 gap-y-1">
          {resumen.map(([etiqueta, valor]) => (
            <div key={etiqueta} className="contents">
              <dt className="text-muted">{etiqueta}</dt>
              <dd className="text-right font-semibold tabular-nums">{valor}</dd>
            </div>
          ))}
        </dl>

        {/* Mismo campo para las dos decisiones: al rechazar es el motivo
            (obligatorio, Romana lo ve al volver a pesar); al aprobar es un
            comentario opcional de por qué se acepta. */}
        <label className="flex flex-col gap-1">
          <span className="font-semibold">
            {decision === 'rechazar' ? 'Motivo del rechazo' : 'Comentario (opcional)'}
          </span>
          <textarea
            ref={campoMotivo}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            disabled={enviando}
            rows={3}
            required={decision === 'rechazar'}
            aria-describedby={idAyudaMotivo}
            className="w-full resize-y rounded-control border border-borde bg-fondo px-2 py-1 text-texto outline-none focus:border-acento"
          />
          <span id={idAyudaMotivo} className="text-muted">
            {decision === 'rechazar'
              ? `Obligatorio, al menos ${MOTIVO_MINIMO} caracteres. Queda registrado en la pesada.`
              : 'Por qué se aprueba, por ejemplo una diferencia con la guía que está justificada. Queda registrado en la pesada.'}
          </span>
        </label>

        {error && (
          <p role="alert" className="flex items-center gap-1">
            <Punto color="bg-error" />
            {error}
          </p>
        )}

        <div className="flex flex-wrap justify-end gap-1">
          <button
            ref={botonCancelar}
            type="button"
            onClick={onCerrar}
            disabled={enviando}
            className="h-6 rounded-control border border-borde px-3 transition-colors hover:bg-borde disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => void confirmar()}
            disabled={!puedeConfirmar}
            className="h-6 rounded-control bg-acento px-3 font-semibold text-blanco transition-colors hover:bg-acento-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {enviando ? 'Enviando…' : textos.confirmar}
          </button>
        </div>
      </div>
    </div>
  )
}
