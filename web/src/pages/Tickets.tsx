import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { buscarKardex, LIMITE_KARDEX, type FiltrosKardex } from '../api/pesadas'
import { DetallePesada } from '../components/DetallePesada'
import { BotonTicket } from '../components/ListaPesadas'
import { Marco, type PropsPagina } from '../components/Marco'
import { Punto } from '../components/Punto'
import { FilaKpis, TarjetaKpi } from '../components/TarjetaKpi'
import { useDatosEnVivo } from '../hooks/useDatosEnVivo'
import type { Pesada } from '../types/pesada'
import { ESTADOS_PESADA, estadoDePesada } from '../utils/estadoPesada'
import { fechaHora, ultimosDias } from '../utils/fechas'
import { formatearKg } from '../utils/pesadas'

const CAMPO =
  'h-5 rounded-control border border-borde bg-fondo px-2 text-texto outline-none focus:border-acento'
const TH = 'px-2 text-left font-semibold text-muted'
const TD = 'px-2'

/** Minúsculas y sin tildes: "Maíz" se encuentra escribiendo "maiz". */
function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
}

/** Lo que se busca con el texto libre: ticket, placa, producto y empresas. */
function textoBuscable(p: Pesada): string {
  return normalizar(
    [
      p.numero_ticket,
      p.vehiculo?.placa,
      p.producto?.nombre,
      p.empresa_cliente_proveedor,
      p.proveedor?.nombre,
      p.empresa_transportista,
      p.transportista?.nombre,
    ]
      .filter(Boolean)
      .join(' '),
  )
}

const claveDe = (f: FiltrosKardex) => `${f.desde}|${f.hasta}|${f.estado}`

/**
 * Historial de pesadas (el kardex del backend) con el mismo panel de
 * detalle que el tablero. Fechas y estado se filtran en el SERVIDOR (el
 * historial crece sin límite); el texto libre, sobre lo ya traído, sin
 * volver a pedir nada.
 */
export function Tickets(props: PropsPagina) {
  const [filtros, setFiltros] = useState<FiltrosKardex>(() => ({ ...ultimosDias(7), estado: '' }))
  const [texto, setTexto] = useState('')
  const [abierta, setAbierta] = useState<Pesada | null>(null)
  const cerrarDetalle = useCallback(() => setAbierta(null), [])

  const rangoInvalido = filtros.desde !== '' && filtros.hasta !== '' && filtros.desde > filtros.hasta

  // Cada respuesta viaja con la clave de los filtros que la pidieron: así
  // se sabe si lo que hay en pantalla corresponde a los filtros actuales.
  const traer = useCallback(
    async (token: string) => {
      const clave = claveDe(filtros)
      if (rangoInvalido) return { clave, pesadas: [] as Pesada[] }
      return { clave, pesadas: await buscarKardex(token, filtros) }
    },
    [filtros, rangoInvalido],
  )
  const { datos, error, actualizado, conectado, recargar } = useDatosEnVivo(
    props.sesion.token,
    traer,
    props.onCerrarSesion,
  )

  // useDatosEnVivo carga una vez al montar y ante cada evento del
  // WebSocket, pero no cuando cambia `traer`. Si los datos en pantalla
  // son de otros filtros, se piden de nuevo. Esto también corrige el caso
  // de respuestas que llegan desordenadas (una recarga vieja que aterriza
  // después de la nueva): vuelve a no coincidir y se repide.
  const claveActual = claveDe(filtros)
  const desactualizado = datos !== null && datos.clave !== claveActual
  // `recargar` es una función nueva en cada render: va en un ref para que
  // el efecto dependa solo del cambio de filtros y no pida en cada render.
  const recargarRef = useRef(recargar)
  useEffect(() => {
    recargarRef.current = recargar
  })
  useEffect(() => {
    if (desactualizado) recargarRef.current()
  }, [desactualizado, claveActual, datos?.clave])

  const visibles = useMemo(() => {
    const pesadas = datos?.pesadas ?? []
    const buscado = normalizar(texto.trim())
    if (!buscado) return pesadas
    return pesadas.filter((p) => textoBuscable(p).includes(buscado))
  }, [datos, texto])

  const completadas = visibles.filter((p) => p.estado === 'completado')
  const netoCompletadas = completadas.reduce((total, p) => total + (p.peso_neto ?? 0), 0)
  const anuladas = visibles.filter((p) => p.estado === 'anulado').length
  const enCurso = visibles.length - completadas.length - anuladas
  const llegoAlTope = (datos?.pesadas.length ?? 0) >= LIMITE_KARDEX

  const cambiar = (cambio: Partial<FiltrosKardex>) => setFiltros((f) => ({ ...f, ...cambio }))

  return (
    <Marco
      {...props}
      titulo="Tickets"
      descripcion="Historial de pesadas por fecha de entrada. Clic en un ticket para ver todo su recorrido."
      conectado={conectado}
      actualizado={actualizado}
      error={error}
      onReintentar={recargar}
    >
      <div className="flex flex-wrap items-end gap-2 rounded-card border border-borde bg-card p-3">
        <label className="flex flex-col gap-1">
          <span className="text-muted">Desde</span>
          <input
            type="date"
            value={filtros.desde}
            max={filtros.hasta || undefined}
            onChange={(e) => cambiar({ desde: e.target.value })}
            className={CAMPO}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-muted">Hasta</span>
          <input
            type="date"
            value={filtros.hasta}
            min={filtros.desde || undefined}
            onChange={(e) => cambiar({ hasta: e.target.value })}
            className={CAMPO}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-muted">Estado</span>
          <select
            value={filtros.estado}
            onChange={(e) => cambiar({ estado: e.target.value })}
            className={CAMPO}
          >
            <option value="">Todos</option>
            {ESTADOS_PESADA.map((e) => (
              <option key={e.valor} value={e.valor}>
                {e.etiqueta}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-30 flex-1 flex-col gap-1">
          <span className="text-muted">Buscar</span>
          <input
            type="search"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Ticket, placa, producto o empresa"
            className={CAMPO}
          />
        </label>
      </div>

      {rangoInvalido && (
        <p role="alert" className="flex items-center gap-1">
          <Punto color="bg-advertencia" />
          La fecha Desde es posterior a Hasta: no hay nada que buscar.
        </p>
      )}

      {!datos ? (
        !error && <p className="text-muted">Cargando historial…</p>
      ) : desactualizado ? (
        !error && <p className="text-muted">Buscando…</p>
      ) : (
        <>
          <FilaKpis>
            <TarjetaKpi
              etiqueta="Pesadas"
              valor={String(visibles.length)}
              detalle={texto.trim() ? 'Que coinciden con la búsqueda' : 'En el período elegido'}
            />
            <TarjetaKpi
              etiqueta="Completadas"
              valor={String(completadas.length)}
              detalle={`${enCurso} en curso · ${anuladas} ${anuladas === 1 ? 'anulada' : 'anuladas'}`}
            />
            <TarjetaKpi
              etiqueta="Neto completado"
              valor={`${formatearKg(netoCompletadas)} kg`}
              // Solo las completadas: en las demás el neto todavía puede
              // cambiar (o ya no cuenta, si se anularon).
              detalle="Suma de las pesadas completadas"
            />
            <TarjetaKpi
              etiqueta="Neto promedio"
              valor={
                completadas.length ? `${formatearKg(netoCompletadas / completadas.length)} kg` : '—'
              }
              detalle="Por pesada completada"
            />
          </FilaKpis>

          {llegoAlTope && (
            <p role="status" className="flex items-center gap-1">
              <Punto color="bg-advertencia" />
              Se muestran solo las {LIMITE_KARDEX} pesadas más recientes del período. Acorte las
              fechas para ver el resto.
            </p>
          )}

          <TablaTickets pesadas={visibles} onAbrir={setAbierta} />
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
    </Marco>
  )
}

function TablaTickets({ pesadas, onAbrir }: { pesadas: Pesada[]; onAbrir: (p: Pesada) => void }) {
  if (pesadas.length === 0) {
    return (
      <p className="rounded-card border border-borde bg-card p-4 text-center text-muted">
        No hay pesadas para estos filtros.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-card border border-borde bg-card">
      <table className="w-full min-w-100 border-collapse">
        <thead>
          <tr className="h-6 border-b border-borde">
            <th className={TH}>Ticket</th>
            <th className={TH}>Entrada</th>
            <th className={TH}>Placa</th>
            <th className={TH}>Producto / Empresa</th>
            <th className={TH}>Estado</th>
            <th className={`${TH} text-right`}>Neto (kg)</th>
          </tr>
        </thead>
        <tbody>
          {pesadas.map((p) => {
            const estado = estadoDePesada(p.estado)
            return (
              <tr
                key={p.id}
                onClick={() => onAbrir(p)}
                className="h-6 cursor-pointer border-b border-borde transition-colors last:border-0 hover:bg-borde"
              >
                <td className={TD}>
                  <BotonTicket pesada={p} onAbrir={onAbrir} />
                  {p.es_manual && (
                    <span className="ml-1 text-muted" title="El peso se cargó a mano, no lo tomó la báscula">
                      manual
                    </span>
                  )}
                </td>
                <td className={`${TD} text-muted tabular-nums`}>{fechaHora(p.fecha_entrada)}</td>
                <td className={TD}>{p.vehiculo?.placa ?? '—'}</td>
                <td className={`${TD} text-muted`}>
                  {p.producto?.nombre ?? p.empresa_cliente_proveedor ?? p.empresa_transportista ?? '—'}
                </td>
                <td className={TD}>
                  <span className="flex items-center gap-1">
                    <Punto color={estado.punto} />
                    {estado.etiqueta}
                  </span>
                </td>
                <td className={`${TD} text-right tabular-nums`}>{formatearKg(p.peso_neto)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
