import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PALETAS } from '../tema'
import type { EstadisticasSeries } from '../types/estadisticas'
import PanelGraficos from './Graficos'

// En archivo aparte y con import directo (no lazy): cargar Recharts
// tarda más que el límite de un test, y el costo de importar un módulo
// no cuenta contra ese reloj. Acá se verifica que los gráficos se
// dibujan; que se carguen aparte se verifica en pantallas.test.tsx.

function estadisticas(parcial: Partial<EstadisticasSeries> = {}): EstadisticasSeries {
  return {
    dias: 2,
    generado: new Date().toISOString(),
    kpis: {
      en_planta: 0,
      pendientes_aprobacion: 0,
      completadas_hoy: 0,
      neto_hoy_kg: 0,
      minutos_promedio_hoy: null,
      porcentaje_auto_aprobadas: null,
    },
    serie_diaria: [
      { fecha: '2026-09-21', completadas: 2, minutos_promedio: 120 },
      { fecha: '2026-09-22', completadas: 4, minutos_promedio: 135 },
    ],
    distribucion_tipo: [{ tipo: 'PRODUCTO_TERMINADO', cantidad: 5 }],
    ...parcial,
  }
}

describe('PanelGraficos', () => {
  it('dibuja los tres gráficos', () => {
    render(<PanelGraficos estadisticas={estadisticas()} colores={PALETAS.claro} />)

    for (const titulo of [
      'Tiempo promedio de liberación',
      'Pesadas completadas por día',
      'Distribución por tipo de pesaje',
    ]) {
      expect(screen.getByRole('heading', { name: titulo })).toBeDefined()
    }
  })

  it('avisa cuando no hay datos, en vez de mostrar un gráfico vacío', () => {
    render(
      <PanelGraficos
        estadisticas={estadisticas({
          serie_diaria: [
            { fecha: '2026-09-21', completadas: 0, minutos_promedio: null },
            { fecha: '2026-09-22', completadas: 0, minutos_promedio: null },
          ],
          distribucion_tipo: [],
        })}
        colores={PALETAS.claro}
      />,
    )

    expect(screen.getAllByText(/Todavía no hay datos suficientes/)).toHaveLength(3)
  })
})
