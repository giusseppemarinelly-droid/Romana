import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TAMANO_CUERPO, type Paleta } from '../tema'
import type { DistribucionTipo, EstadisticasSeries, PuntoSerie } from '../types/estadisticas'
import { fechaCorta, formatearMinutos } from '../utils/tiempo'

// Todo color sale de la paleta del tema activo (src/tema.ts): Recharts
// trae grises, blancos y un tooltip claro por defecto que desentonan.
function estilosBase(c: Paleta) {
  return {
    eje: { fill: c.muted, fontSize: TAMANO_CUERPO },
    lineaEje: { stroke: c.borde },
    tooltip: {
      contentStyle: {
        background: c.card,
        border: `1px solid ${c.borde}`,
        borderRadius: 8,
        fontSize: TAMANO_CUERPO,
        color: c.texto,
      },
      labelStyle: { color: c.muted },
      itemStyle: { color: c.texto },
    },
  }
}
const MARGEN = { top: 8, right: 16, bottom: 0, left: 0 }

function Panel({
  titulo,
  ayuda,
  vacio,
  children,
}: {
  titulo: string
  ayuda: string
  vacio: boolean
  children: React.ReactElement
}) {
  return (
    <section className="flex flex-col gap-2 rounded-card border border-borde bg-card p-3">
      <div className="flex flex-col gap-1">
        <h2 className="text-subtitulo font-semibold">{titulo}</h2>
        <p className="text-muted">{ayuda}</p>
      </div>
      {vacio ? (
        <p className="py-4 text-center text-muted">Todavía no hay datos suficientes para este gráfico.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          {children}
        </ResponsiveContainer>
      )}
    </section>
  )
}

/**
 * Export por defecto para poder cargarlo aparte (lazy) desde
 * Estadísticas: Recharts pesa más que todo el resto de la app junta.
 */
export default function PanelGraficos({
  estadisticas,
  colores,
}: {
  estadisticas: EstadisticasSeries
  colores: Paleta
}) {
  return (
    <div className="grid gap-3 xl:grid-cols-3">
      <GraficoTiempoLiberacion serie={estadisticas.serie_diaria} c={colores} />
      <GraficoVolumenDiario serie={estadisticas.serie_diaria} c={colores} />
      <GraficoDistribucionTipo distribucion={estadisticas.distribucion_tipo} c={colores} />
    </div>
  )
}

export function GraficoTiempoLiberacion({ serie, c }: { serie: PuntoSerie[]; c: Paleta }) {
  const { eje, lineaEje, tooltip } = estilosBase(c)
  const datos = serie.map((p) => ({ ...p, etiqueta: fechaCorta(p.fecha) }))
  const sinDatos = serie.every((p) => p.minutos_promedio === null)

  return (
    <Panel
      titulo="Tiempo promedio de liberación"
      ayuda="Desde que el camión entra hasta que se cierra la pesada"
      vacio={sinDatos}
    >
      <LineChart data={datos} margin={MARGEN}>
        <CartesianGrid stroke={c.borde} vertical={false} />
        <XAxis dataKey="etiqueta" tick={eje} axisLine={lineaEje} tickLine={false} />
        <YAxis tick={eje} width={48} axisLine={false} tickLine={false} />
        <Tooltip
          {...tooltip}
          cursor={{ stroke: c.borde }}
          formatter={(valor) => [formatearMinutos(valor as number), 'Promedio']}
        />
        {/* connectNulls en false: los días sin pesadas quedan como hueco y
            no como una línea recta que inventa una tendencia. */}
        <Line
          type="monotone"
          dataKey="minutos_promedio"
          stroke={c.acento}
          strokeWidth={2}
          connectNulls={false}
          dot={{ r: 3, fill: c.acento, stroke: c.acento }}
          activeDot={{ r: 4, fill: c.acento, stroke: c.card }}
        />
      </LineChart>
    </Panel>
  )
}

export function GraficoVolumenDiario({ serie, c }: { serie: PuntoSerie[]; c: Paleta }) {
  const { eje, lineaEje, tooltip } = estilosBase(c)
  const datos = serie.map((p) => ({ ...p, etiqueta: fechaCorta(p.fecha) }))
  const sinDatos = serie.every((p) => p.completadas === 0)

  return (
    <Panel titulo="Pesadas completadas por día" ayuda="Volumen de cierres diarios" vacio={sinDatos}>
      <BarChart data={datos} margin={MARGEN}>
        <CartesianGrid stroke={c.borde} vertical={false} />
        <XAxis dataKey="etiqueta" tick={eje} axisLine={lineaEje} tickLine={false} />
        <YAxis tick={eje} width={48} allowDecimals={false} axisLine={false} tickLine={false} />
        <Tooltip
          {...tooltip}
          cursor={{ fill: c.borde }}
          formatter={(valor) => [valor as number, 'Completadas']}
        />
        <Bar dataKey="completadas" fill={c.exito} />
      </BarChart>
    </Panel>
  )
}

const NOMBRE_TIPO: Record<string, string> = {
  GENERAL: 'Pesaje General',
  PRODUCTO_TERMINADO: 'Producto Terminado',
}
export function GraficoDistribucionTipo({
  distribucion,
  c,
}: {
  distribucion: DistribucionTipo[]
  c: Paleta
}) {
  const { tooltip } = estilosBase(c)
  const colorTipo: Record<string, string> = { PRODUCTO_TERMINADO: c.acento, GENERAL: c.muted }
  const datos = distribucion.map((d) => ({
    nombre: NOMBRE_TIPO[d.tipo] ?? d.tipo,
    cantidad: d.cantidad,
    color: colorTipo[d.tipo] ?? c.advertencia,
  }))

  return (
    <Panel
      titulo="Distribución por tipo de pesaje"
      ayuda="Sobre las pesadas cerradas en el período"
      vacio={datos.length === 0}
    >
      <PieChart>
        <Pie
          data={datos}
          dataKey="cantidad"
          nameKey="nombre"
          innerRadius={56}
          outerRadius={88}
          stroke={c.card}
          strokeWidth={2}
        >
          {datos.map((d) => (
            <Cell key={d.nombre} fill={d.color} />
          ))}
        </Pie>
        <Tooltip {...tooltip} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: TAMANO_CUERPO }}
          formatter={(valor) => <span style={{ color: c.muted }}>{valor}</span>}
        />
      </PieChart>
    </Panel>
  )
}
