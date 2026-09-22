import { lazy, Suspense, useCallback } from 'react'
import { obtenerEstadisticas } from '../api/estadisticas'
import { Marco, type PropsPagina } from '../components/Marco'
import { FilaKpis, TarjetaKpi } from '../components/TarjetaKpi'
import { useDatosEnVivo } from '../hooks/useDatosEnVivo'
import { PALETAS } from '../tema'
import { resumirSerie } from '../utils/resumenSerie'
import { formatearMinutos } from '../utils/tiempo'

const DIAS_DE_HISTORIA = 14

// Recharts pesa más que todo el resto de la app junta: se descarga recién
// cuando alguien entra a esta pantalla, no al abrir la web.
const PanelGraficos = lazy(() => import('../components/Graficos'))

export function Estadisticas(props: PropsPagina) {
  const traer = useCallback((token: string) => obtenerEstadisticas(token, DIAS_DE_HISTORIA), [])
  const { datos, error, actualizado, conectado, recargar } = useDatosEnVivo(
    props.sesion.token,
    traer,
    props.onCerrarSesion,
  )

  const resumen = datos ? resumirSerie(datos.serie_diaria) : null
  const auto = datos?.kpis.porcentaje_auto_aprobadas ?? null

  return (
    <Marco
      {...props}
      titulo="Estadísticas"
      descripcion={`Pesadas cerradas en los últimos ${DIAS_DE_HISTORIA} días.`}
      conectado={conectado}
      actualizado={actualizado}
      error={error}
      onReintentar={recargar}
    >
      {!datos || !resumen ? (
        !error && <p className="text-muted">Cargando datos…</p>
      ) : (
        <>
          <FilaKpis>
            <TarjetaKpi
              etiqueta="Aprobación automática"
              valor={auto === null ? '—' : `${auto}%`}
              detalle="No pasaron por Costos: dentro de la tolerancia contra la guía"
            />
            <TarjetaKpi
              etiqueta="Pesadas cerradas"
              valor={String(resumen.completadas)}
              detalle={`En ${DIAS_DE_HISTORIA} días`}
            />
            <TarjetaKpi
              etiqueta="Promedio diario"
              valor={resumen.promedioDiario.toLocaleString('es-VE', { maximumFractionDigits: 1 })}
              detalle="Cierres por día"
            />
            <TarjetaKpi
              etiqueta="Liberación promedio"
              valor={formatearMinutos(resumen.minutosPromedio)}
              detalle="Desde la entrada hasta el cierre"
            />
          </FilaKpis>

          <Suspense fallback={<p className="text-muted">Cargando gráficos…</p>}>
            <PanelGraficos estadisticas={datos} colores={PALETAS[props.tema]} />
          </Suspense>
        </>
      )}
    </Marco>
  )
}
