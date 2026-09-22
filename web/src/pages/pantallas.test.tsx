import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Sesion } from '../types/auth'
import type { Pesada } from '../types/pesada'
import { Costos } from './Costos'
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

class WebSocketFalso {
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  close() {}
}

const sesion: Sesion = {
  token: 'token-de-prueba',
  usuario: {
    id: 1,
    username: 'supervisor',
    nombre_completo: 'Supervisor de Planta',
    nivel: 2,
    activo: true,
    last_login: null,
  },
  nivelNombre: 'Supervisor',
  expiraEn: Date.now() + 3_600_000,
}

function pesada(parcial: Partial<Pesada>): Pesada {
  return {
    id: 1,
    numero_ticket: 'TK-000001',
    estado: 'en_planta',
    tipo_pesaje: 'PRODUCTO_TERMINADO',
    fecha_entrada: new Date().toISOString(),
    fecha_captura: new Date().toISOString(),
    fecha_aprobacion: null,
    fecha_salida: null,
    peso_entrada: 10_000,
    peso_bruto: 20_000,
    peso_tara: 10_000,
    peso_neto: 10_000,
    codigo_viaje: '150',
    peso_guia: 12_000,
    bultos: 15,
    auto_aprobado: false,
    es_manual: false,
    empresa_transportista: null,
    empresa_cliente_proveedor: 'Farmatodo',
    vehiculo: { placa: 'ABC-123', descripcion: null },
    producto: { codigo: '001', nombre: 'Producto Terminado' },
    ...parcial,
  }
}

const ESTADISTICAS = {
  dias: 14,
  generado: new Date().toISOString(),
  kpis: {
    en_planta: 1,
    pendientes_aprobacion: 1,
    completadas_hoy: 4,
    neto_hoy_kg: 40_000,
    minutos_promedio_hoy: 135,
    porcentaje_auto_aprobadas: 62.5,
  },
  serie_diaria: [
    { fecha: '2026-09-21', completadas: 2, minutos_promedio: 120 },
    { fecha: '2026-09-22', completadas: 4, minutos_promedio: 135 },
  ],
  distribucion_tipo: [
    { tipo: 'PRODUCTO_TERMINADO', cantidad: 5 },
    { tipo: 'GENERAL', cantidad: 1 },
  ],
}

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

let llamadas: { url: string; opciones?: RequestInit }[] = []

beforeEach(() => {
  llamadas = []
  vi.stubGlobal('WebSocket', WebSocketFalso)
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, opciones?: RequestInit) => {
      llamadas.push({ url, opciones })
      const clave = Object.keys(POR_RUTA).find((k) => url.includes(k))
      return Promise.resolve(new Response(JSON.stringify(clave ? POR_RUTA[clave] : []), { status: 200 }))
    }),
  )
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

describe('Costos', () => {
  it('muestra la cola con la diferencia contra la guía ya calculada', async () => {
    render(<Costos {...props} pagina="costos" />)

    // Una vez en la tabla y otra en la card "Más antigua en cola".
    expect(await screen.findAllByText('TK-PENDIENTE')).toHaveLength(2)
    // 10.000 vs guía 12.000 = 16,67% fuera de tolerancia
    expect(screen.getByText('16.67 %')).toBeDefined()
    expect(screen.getByText('TK-AUTO')).toBeDefined()
  })

  it('no ofrece ninguna acción de decisión (es solo lectura)', async () => {
    render(<Costos {...props} pagina="costos" />)
    await screen.findAllByText('TK-PENDIENTE')

    const textos = screen.getAllByRole('button').map((b) => b.textContent ?? '')
    expect(textos.some((t) => /aprobar|rechazar|anular/i.test(t))).toBe(false)
  })

  it('solo hace lecturas: ningún request con método de escritura', async () => {
    render(<Costos {...props} pagina="costos" />)
    await screen.findAllByText('TK-PENDIENTE')

    for (const { opciones } of llamadas) {
      expect(opciones?.method ?? 'GET').toBe('GET')
    }
    expect(llamadas.length).toBeGreaterThan(0)
  })
})
