import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ESTADISTICAS, instalarBackendFalso, pesada, sesionDe, type Llamada } from '../pruebas'
import { Dashboard } from './Dashboard'
import { Estadisticas } from './Estadisticas'

// Humo: confirma que las pantallas se dibujan con datos reales del
// backend simulado. Sin esto no habría ninguna verificación automática
// de que no revientan al renderizar (no hay navegador en los tests).

// Los gráficos se simulan acá a propósito: importar Recharts de verdad
// tarda más que el límite de un test y no aporta nada a lo que se está
// probando (que la página arma bien sus partes). Los gráficos reales se
// prueban en components/Graficos.test.tsx.
vi.mock('../components/Graficos', () => ({
  default: () => <div>panel de gráficos</div>,
}))

const sesion = sesionDe(2)

// Ojo con el orden: 'estadisticas/series' y 'kardex/buscar' se buscan
// antes que las rutas de listados, y 'completadas' va último porque
// aparece dentro de otras URLs.
const POR_RUTA: Record<string, unknown> = {
  'estadisticas/series': ESTADISTICAS,
  'kardex/buscar': [pesada({ id: 6, numero_ticket: 'TK-RECHAZADA', estado: 'rechazado' })],
  'en-planta': [pesada({ id: 1, numero_ticket: 'TK-EN-PLANTA' })],
  'pendientes-aprobacion': [
    pesada({ id: 2, numero_ticket: 'TK-PENDIENTE', peso_neto: 10_000, peso_guia: 12_000 }),
  ],
  'aprobadas-pendientes': [pesada({ id: 3, numero_ticket: 'TK-APROBADA' })],
  'auto-aprobadas': [
    pesada({ id: 5, numero_ticket: 'TK-AUTO', auto_aprobado: true, peso_neto: 11_900, peso_guia: 12_000 }),
  ],
  completadas: [pesada({ id: 4, numero_ticket: 'TK-COMPLETADA' })],
}

let llamadas: Llamada[] = []

beforeEach(() => {
  llamadas = instalarBackendFalso(POR_RUTA)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const props = {
  sesion,
  onCerrarSesion: vi.fn(),
  pagina: 'tablero' as const,
  onCambiarPagina: vi.fn(),
  tema: 'claro' as const,
  onAlternarTema: vi.fn(),
}

describe('Flujo de pesaje', () => {
  it('muestra todas las pesadas en una sola lista, con su estado', async () => {
    render(<Dashboard {...props} />)

    expect(await screen.findByText('TK-EN-PLANTA')).toBeDefined()
    for (const ticket of ['TK-PENDIENTE', 'TK-RECHAZADA', 'TK-APROBADA', 'TK-COMPLETADA']) {
      expect(screen.getByText(ticket)).toBeDefined()
    }
    // El estado dejó de ser una columna y pasó a ser una etiqueta por
    // fila. Se busca dentro de la tabla: "En planta" también aparece en
    // el resumen de arriba y en los filtros.
    const tabla = within(screen.getByRole('table'))
    expect(tabla.getByText('En planta')).toBeDefined()
    expect(tabla.getByText('Rechazada')).toBeDefined()
  })

  it('filtra por estado sin volver a pedirle nada al backend', async () => {
    render(<Dashboard {...props} />)
    await screen.findByText('TK-EN-PLANTA')
    const requestsAntes = llamadas.length

    fireEvent.click(screen.getByRole('button', { name: /Rechazada/ }))

    expect(screen.getByText('TK-RECHAZADA')).toBeDefined()
    expect(screen.queryByText('TK-EN-PLANTA')).toBeNull()
    expect(llamadas.length).toBe(requestsAntes)
  })

  it('arriba muestra los indicadores del día en cards', async () => {
    render(<Dashboard {...props} />)

    await screen.findByText('TK-EN-PLANTA')
    expect(screen.getByText('Liberación promedio hoy')).toBeDefined()
    expect(screen.getByText('2 h 15 min')).toBeDefined() // 135 minutos
  })

  it('no carga gráficos: viven en su propia pantalla', async () => {
    render(<Dashboard {...props} />)
    await screen.findByText('TK-EN-PLANTA')

    expect(screen.queryByText('panel de gráficos')).toBeNull()
  })

  it('la conexión con el servidor está siempre a la vista, en texto', async () => {
    render(<Dashboard {...props} />)
    await screen.findByText('TK-EN-PLANTA')

    // El WebSocket falso nunca abre: tiene que decirlo, no fingir "en vivo".
    expect(screen.getByText('Sin conexión al servidor')).toBeDefined()
  })

  it('el sidebar lleva a las tres secciones', async () => {
    render(<Dashboard {...props} />)
    await screen.findByText('TK-EN-PLANTA')

    fireEvent.click(screen.getByRole('button', { name: 'Estadísticas' }))
    expect(props.onCambiarPagina).toHaveBeenCalledWith('estadisticas')
    expect(screen.getByRole('button', { name: 'Pesajes en vivo' }).getAttribute('aria-current')).toBe(
      'page',
    )
  })

  it('el botón de tema del sidebar ofrece el modo oscuro', async () => {
    render(<Dashboard {...props} />)
    await screen.findByText('TK-EN-PLANTA')

    fireEvent.click(screen.getByRole('button', { name: 'Modo oscuro' }))
    expect(props.onAlternarTema).toHaveBeenCalled()
  })
})

describe('Centro de Costos en la web (nivel 4)', () => {
  it('ve el tablero sin pedir el kardex, que no tiene permitido', async () => {
    render(<Dashboard {...props} sesion={sesionDe(4)} />)

    expect(await screen.findByText('TK-EN-PLANTA')).toBeDefined()
    expect(llamadas.some((l) => l.url.includes('kardex'))).toBe(false)
  })

  it('en el sidebar ve Costos pero no Tickets ni Maestros', async () => {
    render(<Dashboard {...props} sesion={sesionDe(4)} />)
    await screen.findByText('TK-EN-PLANTA')

    expect(screen.getByRole('button', { name: 'Costos' })).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Tickets' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Maestros' })).toBeNull()
  })
})

describe('Estadísticas', () => {
  it('muestra los KPIs del período y los gráficos', async () => {
    render(<Estadisticas {...props} pagina="estadisticas" />)

    expect(await screen.findByText('Aprobación automática')).toBeDefined()
    expect(screen.getByText('62.5%')).toBeDefined()
    expect(screen.getByText('Pesadas cerradas')).toBeDefined()
    expect(screen.getByText('6')).toBeDefined() // 2 + 4 de la serie
    expect(await screen.findByText('panel de gráficos')).toBeDefined()
  })
})
