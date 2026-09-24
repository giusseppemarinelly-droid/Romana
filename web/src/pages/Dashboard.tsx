import { useCallback, useMemo, useState } from 'react'
import { obtenerEstadisticas } from '../api/estadisticas'
import { obtenerTablero } from '../api/pesadas'
import { DetallePesada } from '../components/DetallePesada'
import { FiltrosEstado, type Filtro } from '../components/FiltrosEstado'
import { ListaPesadas } from '../components/ListaPesadas'
import { Marco, type PropsPagina } from '../components/Marco'
import { Punto } from '../components/Punto'
import { FilaKpis, TarjetaKpi } from '../components/TarjetaKpi'
import { useDatosEnVivo } from '../hooks/useDatosEnVivo'
import type { Pesada } from '../types/pesada'
import { formatearKg } from '../utils/pesadas'
import { aplanarTablero, type ClaveEstado, type FilaPesada } from '../utils/tablero'
import { formatearMinutos } from '../utils/tiempo'

async function traerTodo(token: string, nivel: number) {
  // Solo se necesitan los KPIs de hoy, no la serie: con 1 día alcanza.
  const [tablero, estadisticas] = await Promise.all([
    obtenerTablero(token, nivel),
    obtenerEstadisticas(token, 1),
  ])
  return { tablero, kpis: estadisticas.kpis }
}

function Demoradas({ filas, estado }: { filas: FilaPesada[]; estado: ClaveEstado }) {
  const cantidad = filas.filter((f) => f.estado === estado && f.demorada).length
  if (cantidad === 0) return <span>Ninguna demorada</span>
  return (
    <span className="flex items-center gap-1 text-texto">
      <Punto color="bg-error" />
      {cantidad === 1 ? '1 demorada' : `${cantidad} demoradas`}
    </span>
  )
}

export function Dashboard(props: PropsPagina) {
  const nivel = props.sesion.usuario.nivel
  const traer = useCallback((token: string) => traerTodo(token, nivel), [nivel])
  const { datos, error, actualizado, conectado, recargar } = useDatosEnVivo(
    props.sesion.token,
    traer,
    props.onCerrarSesion,
  )
  const [filtro, setFiltro] = useState<Filtro>('todas')
  // La pesada abierta en el panel de detalle (la fila tal como estaba al
  // hacer clic; el panel pide la versión completa al backend).
  const [abierta, setAbierta] = useState<Pesada | null>(null)
  const cerrarDetalle = useCallback(() => setAbierta(null), [])

  const filas = useMemo(() => (datos ? aplanarTablero(datos.tablero) : []), [datos])
  const filasVisibles = filtro === 'todas' ? filas : filas.filter((f) => f.estado === filtro)

  return (
    <Marco
      {...props}
      titulo="Pesajes en vivo"
      descripcion="Lo que más tiempo lleva esperando, primero."
      conectado={conectado}
      actualizado={actualizado}
      error={error}
      onReintentar={recargar}
    >
      {!datos ? (
        !error && <p className="text-muted">Cargando datos…</p>
      ) : (
        <>
          <FilaKpis>
            <TarjetaKpi
              etiqueta="En planta"
              valor={String(datos.kpis.en_planta)}
              detalle={<Demoradas filas={filas} estado="enPlanta" />}
            />
            <TarjetaKpi
              etiqueta="Esperando a Costos"
              valor={String(datos.kpis.pendientes_aprobacion)}
              detalle={<Demoradas filas={filas} estado="pendientesAprobacion" />}
            />
            <TarjetaKpi
              etiqueta="Liberación promedio hoy"
              valor={formatearMinutos(datos.kpis.minutos_promedio_hoy)}
              detalle="Desde la entrada hasta el cierre"
            />
            <TarjetaKpi
              etiqueta="Cerradas hoy"
              valor={String(datos.kpis.completadas_hoy)}
              detalle={`${formatearKg(datos.kpis.neto_hoy_kg)} kg neto`}
            />
          </FilaKpis>

          <div className="flex flex-col gap-2">
            <FiltrosEstado filas={filas} actual={filtro} onCambiar={setFiltro} />
            <ListaPesadas filas={filasVisibles} onAbrir={setAbierta} />
          </div>
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
