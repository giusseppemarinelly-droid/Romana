// Refleja backend/schemas/pesada.py → EstadisticasSeriesOut.

export interface Kpis {
  en_planta: number
  pendientes_aprobacion: number
  completadas_hoy: number
  neto_hoy_kg: number
  /** null cuando no hay datos para calcularlo (no es lo mismo que 0). */
  minutos_promedio_hoy: number | null
  porcentaje_auto_aprobadas: number | null
}

export interface PuntoSerie {
  fecha: string // YYYY-MM-DD
  completadas: number
  minutos_promedio: number | null
}

export interface DistribucionTipo {
  tipo: string
  cantidad: number
}

export interface EstadisticasSeries {
  dias: number
  generado: string
  kpis: Kpis
  serie_diaria: PuntoSerie[]
  distribucion_tipo: DistribucionTipo[]
}
