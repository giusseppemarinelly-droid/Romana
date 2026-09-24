import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { aprobarPesada, rechazarPesada } from '../api/costos'
import { ErrorApi, obtenerAutoAprobadas, obtenerPendientesAprobacion } from '../api/pesadas'
import { DetallePesada } from '../components/DetallePesada'
import { DialogoDecision, type Decision } from '../components/DialogoDecision'
import { BotonTicket } from '../components/ListaPesadas'
import { Marco, type PropsPagina } from '../components/Marco'
import { Punto } from '../components/Punto'
import { FilaKpis, TarjetaKpi } from '../components/TarjetaKpi'
import { useDatosEnVivo } from '../hooks/useDatosEnVivo'
import type { Pesada } from '../types/pesada'
import { puede } from '../utils/permisos'
import { diferenciaConGuia, formatearKg } from '../utils/pesadas'
import { horaCorta, tiempoTranscurrido } from '../utils/tiempo'

async function traerCostos(token: string) {
  const [pendientes, autoAprobadas] = await Promise.all([
    obtenerPendientesAprobacion(token),
    obtenerAutoAprobadas(token),
  ])
  return { pendientes, autoAprobadas }
}

/** La que lleva más tiempo en la cola (la de fecha de captura más vieja). */
function masAntigua(pesadas: Pesada[]): Pesada | null {
  const conFecha = pesadas.filter((p) => p.fecha_captura)
  if (conFecha.length === 0) return null
  return conFecha.reduce((a, b) => (a.fecha_captura! < b.fecha_captura! ? a : b))
}

// Cuánto queda a la vista el aviso "TK-… aprobada": lo suficiente para
// leerlo, sin que quede colgado confundiendo con la próxima decisión.
const DURACION_AVISO_MS = 8_000

interface DecisionEnCurso {
  pesada: Pesada
  decision: Decision
}

export function Costos(props: PropsPagina) {
  // Detalle completo (recorrido, chofer, transportista...) para revisar
  // antes de decidir, el mismo panel que en Pesajes en vivo.
  const [abierta, setAbierta] = useState<Pesada | null>(null)
  const cerrarDetalle = useCallback(() => setAbierta(null), [])
  const { token, usuario } = props.sesion
  const { onCerrarSesion } = props
  const { datos, error, actualizado, conectado, recargar } = useDatosEnVivo(
    token,
    traerCostos,
    onCerrarSesion,
  )
  const antigua = datos ? masAntigua(datos.pendientes) : null

  // El backend es la autoridad real (403 sin el permiso); esto solo evita
  // mostrar botones que después fallarían.
  const puedeDecidir = puede(usuario.nivel, 'centro_costos')

  const [enCurso, setEnCurso] = useState<DecisionEnCurso | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    if (!aviso) return
    const id = window.setTimeout(() => setAviso(null), DURACION_AVISO_MS)
    return () => window.clearTimeout(id)
  }, [aviso])

  const cerrarDialogo = useCallback(() => setEnCurso(null), [])

  async function confirmarDecision(motivo: string) {
    if (!enCurso) return
    const { pesada, decision } = enCurso
    try {
      if (decision === 'aprobar') await aprobarPesada(token, pesada.id, motivo)
      else await rechazarPesada(token, pesada.id, motivo)
    } catch (e) {
      // Token vencido: al login, igual que en las lecturas. Cualquier otro
      // error (ej. otro usuario ya decidió) lo muestra el diálogo.
      if (e instanceof ErrorApi && e.status === 401) {
        onCerrarSesion()
        return
      }
      throw e
    }
    setEnCurso(null)
    setAviso(`${pesada.numero_ticket} ${decision === 'aprobar' ? 'aprobada' : 'rechazada'}`)
    // El WebSocket también avisa, pero es best-effort: la cola propia se
    // recarga siempre, sin depender de él.
    recargar()
  }

  return (
    <Marco
      {...props}
      titulo="Costos"
      descripcion={
        puedeDecidir
          ? 'Pesadas fuera de tolerancia contra la guía. Se pueden aprobar o rechazar desde acá o desde la estación de Centro de Costos.'
          : 'Vista de solo lectura. Aprobar o rechazar se sigue haciendo desde la estación de Centro de Costos.'
      }
      conectado={conectado}
      actualizado={actualizado}
      error={error}
      onReintentar={recargar}
    >
      {!datos ? (
        !error && <p className="text-muted">Cargando…</p>
      ) : (
        <>
          {/* Siempre montado (vacío si no hay aviso): los lectores de
              pantalla anuncian mejor un role="status" que ya existía que
              uno que aparece junto con su texto. */}
          <div role="status">
            {aviso && (
              <p className="flex items-center gap-1 rounded-card border border-borde bg-card px-3 py-2">
                <Punto color="bg-exito" />
                {aviso}
              </p>
            )}
          </div>

          <FilaKpis>
            <TarjetaKpi
              etiqueta="En cola de aprobación"
              valor={String(datos.pendientes.length)}
              detalle="Fuera de tolerancia contra la guía"
            />
            <TarjetaKpi
              etiqueta="Más antigua en cola"
              valor={antigua ? tiempoTranscurrido(antigua.fecha_captura) : '—'}
              detalle={antigua ? antigua.numero_ticket : 'La cola está vacía'}
            />
            <TarjetaKpi
              etiqueta="Auto-aprobadas recientes"
              valor={String(datos.autoAprobadas.length)}
              detalle="Aprobadas solas, sin pasar por Costos"
            />
          </FilaKpis>

          <TablaPendientes
            pesadas={datos.pendientes}
            onDecidir={puedeDecidir ? (pesada, decision) => setEnCurso({ pesada, decision }) : null}
            onAbrir={setAbierta}
          />
          <TablaAutoAprobadas pesadas={datos.autoAprobadas} onAbrir={setAbierta} />
        </>
      )}

      {abierta && (
        <DetallePesada
          key={abierta.id}
          pesada={abierta}
          sesion={props.sesion}
          onCerrar={cerrarDetalle}
          onSesionVencida={props.onCerrarSesion}
          version={actualizado}
        />
      )}

      {enCurso && (
        <DialogoDecision
          // key: si se abre otra decisión sin cerrar la anterior, arranca
          // de cero (motivo y error vacíos) en vez de heredar el estado.
          key={`${enCurso.pesada.id}-${enCurso.decision}`}
          pesada={enCurso.pesada}
          decision={enCurso.decision}
          onConfirmar={confirmarDecision}
          onCerrar={cerrarDialogo}
        />
      )}
    </Marco>
  )
}

function Seccion({
  titulo,
  ayuda,
  cantidad,
  children,
}: {
  titulo: string
  ayuda: string
  cantidad: number
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-col gap-1">
        <h2 className="flex items-center gap-1 text-subtitulo font-semibold">
          {titulo}
          <span className="font-normal text-muted tabular-nums">· {cantidad}</span>
        </h2>
        <p className="text-muted">{ayuda}</p>
      </div>
      {children}
    </section>
  )
}

function Vacio({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-card border border-borde bg-card p-4 text-center text-muted">{children}</p>
  )
}

function Tabla({ columnas, children }: { columnas: [string, boolean][]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-card border border-borde bg-card">
      <table className="w-full min-w-92 border-collapse">
        <thead>
          <tr className="h-6 border-b border-borde">
            {columnas.map(([nombre, derecha]) => (
              <th
                key={nombre}
                className={`px-2 font-semibold text-muted ${derecha ? 'text-right' : 'text-left'}`}
              >
                {nombre}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

const FILA = 'h-6 border-b border-borde transition-colors last:border-0 hover:bg-borde'
const TD = 'px-2'
const NUM = 'px-2 text-right tabular-nums'

function TablaPendientes({
  pesadas,
  onDecidir,
  onAbrir,
}: {
  pesadas: Pesada[]
  onAbrir: (pesada: Pesada) => void
  /** null = sin permiso `centro_costos`: la tabla queda de solo lectura. */
  onDecidir: ((pesada: Pesada, decision: Decision) => void) | null
}) {
  return (
    <Seccion
      titulo="Cola de aprobación"
      ayuda="Pesadas fuera de tolerancia contra la guía, esperando decisión de Centro de Costos"
      cantidad={pesadas.length}
    >
      {pesadas.length === 0 ? (
        <Vacio>No hay nada esperando aprobación.</Vacio>
      ) : (
        <Tabla
          columnas={[
            ['Ticket', false],
            ['Placa', false],
            ['Producto', false],
            ['Neto (kg)', true],
            ['Guía (kg)', true],
            ['Dif.', true],
            ['Esperando', true],
            ...(onDecidir ? ([['Decisión', true]] as [string, boolean][]) : []),
          ]}
        >
          {pesadas.map((p) => {
            const diferencia = diferenciaConGuia(p)
            return (
              <tr key={p.id} className={FILA}>
                <td className={TD}>
                  <BotonTicket pesada={p} onAbrir={onAbrir} />
                </td>
                <td className={TD}>{p.vehiculo?.placa ?? '—'}</td>
                <td className={`${TD} text-muted`}>
                  {p.producto?.nombre ?? p.empresa_cliente_proveedor ?? '—'}
                </td>
                <td className={NUM}>{formatearKg(p.peso_neto)}</td>
                <td className={`${NUM} text-muted`}>{formatearKg(p.peso_guia)}</td>
                <td className={`${NUM} font-semibold`}>
                  {diferencia === null ? (
                    <span className="text-muted">—</span>
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      <Punto color={diferencia >= 10 ? 'bg-error' : 'bg-advertencia'} />
                      <span>{diferencia.toFixed(2)} %</span>
                    </span>
                  )}
                </td>
                <td className={`${NUM} text-muted`}>{tiempoTranscurrido(p.fecha_captura)}</td>
                {onDecidir && (
                  <td className="px-2 py-1">
                    <div className="flex justify-end gap-1">
                      {/* aria-label con el ticket: en una tabla con varias
                          filas, "Aprobar" a secas no dice cuál. */}
                      <button
                        type="button"
                        aria-label={`Aprobar ${p.numero_ticket}`}
                        onClick={() => onDecidir(p, 'aprobar')}
                        className="h-5 rounded-control bg-acento px-2 font-semibold text-blanco transition-colors hover:bg-acento-hover"
                      >
                        Aprobar
                      </button>
                      <button
                        type="button"
                        aria-label={`Rechazar ${p.numero_ticket}`}
                        onClick={() => onDecidir(p, 'rechazar')}
                        className="h-5 rounded-control border border-borde px-2 transition-colors hover:bg-borde"
                      >
                        Rechazar
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            )
          })}
        </Tabla>
      )}
    </Seccion>
  )
}

function TablaAutoAprobadas({
  pesadas,
  onAbrir,
}: {
  pesadas: Pesada[]
  onAbrir: (pesada: Pesada) => void
}) {
  return (
    <Seccion
      titulo="Auto-aprobadas recientes"
      ayuda="Aprobadas solas por estar dentro de la tolerancia contra el peso de guía"
      cantidad={pesadas.length}
    >
      {pesadas.length === 0 ? (
        <Vacio>Todavía no hay auto-aprobadas.</Vacio>
      ) : (
        <Tabla
          columnas={[
            ['Ticket', false],
            ['Placa', false],
            ['Viaje', false],
            ['Neto (kg)', true],
            ['Guía (kg)', true],
            ['Dif.', true],
            ['Bultos', true],
            ['Hora', true],
          ]}
        >
          {pesadas.map((p) => {
            const diferencia = diferenciaConGuia(p)
            return (
              <tr key={p.id} className={FILA}>
                <td className={TD}>
                  <BotonTicket pesada={p} onAbrir={onAbrir} />
                </td>
                <td className={TD}>{p.vehiculo?.placa ?? '—'}</td>
                <td className={`${TD} text-muted`}>{p.codigo_viaje ?? '—'}</td>
                <td className={NUM}>{formatearKg(p.peso_neto)}</td>
                <td className={`${NUM} text-muted`}>{formatearKg(p.peso_guia)}</td>
                <td className={`${NUM} text-exito`}>
                  {diferencia === null ? '—' : `${diferencia.toFixed(2)} %`}
                </td>
                <td className={`${NUM} text-muted`}>{p.bultos ?? '—'}</td>
                <td className={`${NUM} text-muted`}>{horaCorta(p.fecha_captura)}</td>
              </tr>
            )
          })}
        </Tabla>
      )}
    </Seccion>
  )
}
