import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { ErrorApi, obtenerPesada, obtenerTicketPdf } from '../api/pesadas'
import type { Sesion } from '../types/auth'
import type { Pesada } from '../types/pesada'
import { estadoDePesada, nombreTipoPesaje } from '../utils/estadoPesada'
import { fechaHora } from '../utils/fechas'
import { puede } from '../utils/permisos'
import { diferenciaConGuia, formatearKg } from '../utils/pesadas'
import { armarRecorrido, AVISO_HISTORIAL, type Etapa } from '../utils/recorrido'
import { Punto } from './Punto'

const ENFOCABLES = 'button:not([disabled]), a[href], input:not([disabled])'
const BOTON_SECUNDARIO =
  'h-5 shrink-0 rounded-control border border-borde px-2 transition-colors hover:bg-borde disabled:opacity-50'

// La URL del Blob se revoca con demora: revocarla apenas se abre la
// pestaña puede cortar la carga del PDF antes de que el visor lo lea.
const REVOCAR_URL_MS = 60_000

function conKg(kilos: number | null | undefined) {
  const texto = formatearKg(kilos ?? null)
  return texto === '—' ? texto : `${texto} kg`
}

/** Dato vacío (null, undefined o texto en blanco) -> "—". */
function oGuion(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined) return '—'
  const texto = String(valor).trim()
  return texto === '' ? '—' : texto
}

/**
 * Peso final contra el bruto del pre-pesaje, igual que la pantalla
 * "Completar Pesaje" de escritorio (completar_pesaje_view.py): es un
 * control informativo, sin tolerancia que bloquee nada.
 */
function diferenciaFinal(p: Pesada): string | null {
  if (p.peso_final == null || p.peso_bruto === null) return null
  const diferencia = p.peso_final - p.peso_bruto
  const signo = diferencia > 0 ? '+' : ''
  const porcentaje = p.peso_bruto ? ` (${signo}${((diferencia / p.peso_bruto) * 100).toFixed(2)} %)` : ''
  return `${signo}${formatearKg(diferencia)} kg${porcentaje}`
}

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2 border-t border-borde pt-3">
      <h3 className="text-subtitulo font-semibold">{titulo}</h3>
      {children}
    </section>
  )
}

function ListaDatos({ filas }: { filas: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-2 gap-y-1">
      {filas.map(([etiqueta, valor]) => (
        <div key={etiqueta} className="contents">
          <dt className="text-muted">{etiqueta}</dt>
          <dd className="text-right tabular-nums">{valor}</dd>
        </div>
      ))}
    </dl>
  )
}

function Recorrido({ etapas }: { etapas: Etapa[] }) {
  return (
    <ol className="flex flex-col">
      {etapas.map((etapa, i) => {
        const hecha = etapa.estado === 'hecha'
        return (
          <li key={etapa.clave} className="flex gap-2">
            {/* Riel de la línea de tiempo: punto y trazo hasta la siguiente. */}
            <div className="flex flex-col items-center pt-1">
              <Punto color={etapa.punto} />
              {i < etapas.length - 1 && <span className="w-px flex-1 bg-borde" aria-hidden="true" />}
            </div>
            <div className={`flex flex-1 flex-col gap-1 pb-3 ${hecha ? '' : 'text-muted'}`}>
              <p className="flex flex-wrap items-baseline justify-between gap-x-2">
                <span className="font-semibold">{etapa.titulo}</span>
                <span className="text-muted">
                  {hecha
                    ? fechaHora(etapa.fecha)
                    : etapa.estado === 'pendiente'
                      ? 'Pendiente'
                      : 'No ocurrió'}
                </span>
              </p>
              {hecha && (
                <p className="text-muted">Por: {etapa.responsable ?? 'sin usuario registrado'}</p>
              )}
              {etapa.datos.length > 0 && (
                <p className="flex flex-wrap gap-x-2 tabular-nums">
                  {etapa.datos.map((d) => (
                    <span key={d.etiqueta}>
                      <span className="text-muted">{d.etiqueta}:</span> {d.valor}
                    </span>
                  ))}
                </p>
              )}
              {etapa.nota && <p>{etapa.nota}</p>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

/**
 * Detalle completo de una pesada en un panel lateral: pesos, recorrido
 * por etapas y datos de vehículo/chofer/empresas.
 *
 * `pesada` es la fila de la lista que lo abrió: se usa para dibujar el
 * encabezado al instante mientras llega el detalle completo por
 * GET /pesadas/{id} (los listados no garantizan traer todo). `version`
 * cambia cuando la pantalla de atrás recargó datos (evento del
 * WebSocket): ahí se vuelve a pedir, así el detalle no queda viejo.
 *
 * Panel propio (no <dialog>.showModal(), que jsdom no implementa), con el
 * mismo manejo de foco que DialogoDecision: foco adentro al abrir, Tab
 * atrapado, Escape cierra y el foco vuelve a quien lo abrió.
 */
export function DetallePesada({
  pesada: inicial,
  sesion,
  onCerrar,
  onSesionVencida,
  version,
}: {
  pesada: Pesada
  sesion: Sesion
  onCerrar: () => void
  onSesionVencida: () => void
  version?: string | null
}) {
  const idTitulo = useId()
  const [detalle, setDetalle] = useState<Pesada | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [intento, setIntento] = useState(0)
  const [abriendoPdf, setAbriendoPdf] = useState(false)
  const [errorPdf, setErrorPdf] = useState<string | null>(null)

  const panel = useRef<HTMLDivElement>(null)
  const botonCerrar = useRef<HTMLButtonElement>(null)
  const [quienAbrio] = useState(() => document.activeElement as HTMLElement | null)

  const token = sesion.token
  const id = inicial.id

  useEffect(() => {
    botonCerrar.current?.focus()
    return () => quienAbrio?.focus()
  }, [quienAbrio])

  useEffect(() => {
    function alTeclear(e: globalThis.KeyboardEvent) {
      if (e.key === 'Escape') onCerrar()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [onCerrar])

  useEffect(() => {
    let vigente = true
    obtenerPesada(token, id)
      .then((p) => {
        if (!vigente) return
        setDetalle(p)
        setError(null)
      })
      .catch((e: unknown) => {
        if (!vigente) return
        if (e instanceof ErrorApi && e.status === 401) {
          onSesionVencida()
          return
        }
        setError(e instanceof Error ? e.message : 'No se pudo cargar el detalle.')
      })
    return () => {
      vigente = false
    }
  }, [token, id, version, intento, onSesionVencida])

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

  async function verTicket() {
    // La pestaña se abre ANTES del await: abrirla después de una espera
    // la bloquea el bloqueador de ventanas emergentes (ya no cuenta como
    // respuesta directa al clic).
    const pestana = window.open('', '_blank')
    setAbriendoPdf(true)
    setErrorPdf(null)
    try {
      const pdf = await obtenerTicketPdf(token, id)
      const url = URL.createObjectURL(pdf)
      if (pestana) {
        pestana.location.href = url
      } else {
        // Bloqueada igual: se descarga en vez de abrirse.
        const enlace = document.createElement('a')
        enlace.href = url
        enlace.download = `TICKET_${inicial.numero_ticket}.pdf`
        enlace.click()
      }
      window.setTimeout(() => URL.revokeObjectURL(url), REVOCAR_URL_MS)
    } catch (e) {
      pestana?.close()
      if (e instanceof ErrorApi && e.status === 401) {
        onSesionVencida()
        return
      }
      setErrorPdf(e instanceof Error ? e.message : 'No se pudo abrir el ticket.')
    } finally {
      setAbriendoPdf(false)
    }
  }

  const p = detalle ?? inicial
  const estado = estadoDePesada(p.estado)
  const diferenciaGuia = diferenciaConGuia(p)
  const difFinal = diferenciaFinal(p)

  const pesos: [string, ReactNode][] = [
    ['Entrada', conKg(p.peso_entrada)],
    ['Tara', conKg(p.peso_tara)],
    ['Bruto', conKg(p.peso_bruto)],
    ['Neto', <strong key="neto">{conKg(p.peso_neto)}</strong>],
    ...(p.peso_final != null
      ? ([
          ['Peso final', conKg(p.peso_final)],
          ['Peso final vs. bruto', difFinal ?? '—'],
        ] as [string, ReactNode][])
      : []),
  ]
  const guia: [string, ReactNode][] = [
    ['Código de viaje', oGuion(p.codigo_viaje)],
    ['Peso guía', conKg(p.peso_guia)],
    ['Bultos', oGuion(p.bultos)],
    ['Diferencia con guía', diferenciaGuia === null ? '—' : `${diferenciaGuia.toFixed(2)} %`],
  ]

  const vehiculo = p.vehiculo
    ? [p.vehiculo.placa, p.vehiculo.descripcion, p.vehiculo.tipo].filter(Boolean).join(' · ')
    : null
  const chofer = p.conductor
    ? `${p.conductor.nombre} · ${p.conductor.documento}`
    : p.cedula_conductor_libre
  const conCodigo = (e: { nombre: string; codigo: string } | null | undefined) =>
    e ? `${e.nombre} (${e.codigo})` : null
  const datos: [string, ReactNode][] = [
    ['Vehículo', oGuion(vehiculo)],
    ['Chofer', oGuion(chofer)],
    ['Transportista', oGuion(conCodigo(p.transportista) ?? p.empresa_transportista)],
    ['Cliente / proveedor', oGuion(conCodigo(p.proveedor) ?? p.empresa_cliente_proveedor)],
    ['Producto', oGuion(conCodigo(p.producto))],
    ['Procedencia', oGuion(p.procedencia)],
    ['Destino', oGuion(p.destino?.nombre)],
    ['Precintos', oGuion(p.precintos)],
    ['Orden de compra', oGuion(p.orden_compra)],
  ]

  return (
    <div className="fixed inset-0 z-10 flex justify-end">
      {/* Fondo: un clic afuera cierra (acá no hay nada escrito que perder). */}
      <div className="absolute inset-0 bg-fondo/80" onClick={onCerrar} aria-hidden="true" />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        onKeyDown={atraparFoco}
        className="relative flex h-full w-full flex-col gap-3 overflow-y-auto border-l border-borde bg-card p-3 sm:w-60"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col gap-1">
            <h2 id={idTitulo} className="text-titulo font-bold">
              Ticket {p.numero_ticket}
            </h2>
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="flex items-center gap-1 font-semibold">
                <Punto color={estado.punto} />
                {estado.etiqueta}
              </span>
              <span className="text-muted">{nombreTipoPesaje(p.tipo_pesaje)}</span>
              {p.es_manual && (
                <span className="text-muted" title="Algún peso se cargó a mano, no lo tomó la báscula">
                  Peso manual
                </span>
              )}
              {p.auto_aprobado && <span className="text-muted">Auto-aprobada</span>}
            </p>
          </div>
          <button
            ref={botonCerrar}
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar detalle"
            className={BOTON_SECUNDARIO}
          >
            Cerrar
          </button>
        </div>

        {puede(sesion.usuario.nivel, 'reportes_ver') && (
          <div className="flex flex-col gap-1">
            <button
              type="button"
              onClick={() => void verTicket()}
              disabled={abriendoPdf}
              className={`${BOTON_SECUNDARIO} self-start`}
            >
              {abriendoPdf ? 'Abriendo ticket…' : 'Ver ticket PDF'}
            </button>
            {errorPdf && (
              <p role="alert" className="flex items-center gap-1">
                <Punto color="bg-error" />
                {errorPdf}
              </p>
            )}
          </div>
        )}

        {error && (
          <div role="alert" className="flex items-center justify-between gap-2 rounded-card border border-error p-2">
            <span className="flex items-center gap-1">
              <Punto color="bg-error" />
              {error}
            </span>
            <button type="button" onClick={() => setIntento((n) => n + 1)} className={BOTON_SECUNDARIO}>
              Reintentar
            </button>
          </div>
        )}
        {!detalle && !error && <p className="text-muted">Cargando detalle…</p>}

        {detalle && (
          <>
            <Seccion titulo="Pesos">
              <ListaDatos filas={pesos} />
              <h4 className="font-semibold">Guía del transportista</h4>
              <ListaDatos filas={guia} />
            </Seccion>

            <Seccion titulo="Recorrido">
              <Recorrido etapas={armarRecorrido(detalle)} />
              <p className="text-muted">{AVISO_HISTORIAL}</p>
            </Seccion>

            <Seccion titulo="Datos">
              <ListaDatos filas={datos} />
              {oGuion(detalle.observaciones) !== '—' && (
                <div className="flex flex-col gap-1">
                  <p className="text-muted">Observaciones</p>
                  <p className="whitespace-pre-wrap">{detalle.observaciones}</p>
                </div>
              )}
            </Seccion>
          </>
        )}
      </div>
    </div>
  )
}
