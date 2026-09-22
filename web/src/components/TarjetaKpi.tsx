import type { ReactNode } from 'react'

/** Card de indicador: etiqueta, valor grande y, opcional, un detalle abajo. */
export function TarjetaKpi({
  etiqueta,
  valor,
  detalle,
}: {
  etiqueta: string
  valor: string
  detalle?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-1 rounded-card border border-borde bg-card p-3">
      <p className="text-muted">{etiqueta}</p>
      <p className="text-kpi font-bold tabular-nums">{valor}</p>
      {detalle && <div className="text-muted">{detalle}</div>}
    </div>
  )
}

/** Fila de KPIs: se reacomoda sola según el ancho disponible. */
export function FilaKpis({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">{children}</div>
}
