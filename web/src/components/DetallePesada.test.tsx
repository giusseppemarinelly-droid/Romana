import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Dashboard } from '../pages/Dashboard'
import { ESTADISTICAS, instalarBackendFalso, pesada, sesionDe, type Llamada } from '../pruebas'

// El detalle se prueba abierto desde el tablero, como lo usa la gente:
// clic en una fila -> GET /pesadas/{id} -> panel con pesos, recorrido y datos.

const DETALLE = pesada({
  id: 7,
  numero_ticket: 'TK-000007',
  estado: 'completado',
  fecha_entrada: '2026-09-24T08:00:00',
  fecha_captura: '2026-09-24T09:00:00',
  fecha_aprobacion: '2026-09-24T09:30:00',
  fecha_salida: '2026-09-24T10:00:00',
  peso_entrada: 10_000,
  peso_tara: 10_000,
  peso_bruto: 25_000,
  peso_neto: 15_000,
  peso_final: 25_040,
  es_manual: true,
  conductor: { nombre: 'José Pérez', documento: 'V-12345678' },
  transportista: { codigo: 'T01', nombre: 'Transportes Carabobo' },
  proveedor: { codigo: 'C01', nombre: 'Farmatodo' },
  procedencia: 'Valencia',
  precintos: 'A-1, A-2',
  observaciones: 'Llegó con lona rota',
  usuario_entrada: { id: 3, username: 'romana', nombre_completo: 'Ana Romana' },
  aprobado_por: { id: 4, username: 'costos', nombre_completo: 'Carla Costos' },
})

const POR_RUTA: Record<string, unknown> = {
  'estadisticas/series': ESTADISTICAS,
  'kardex/buscar': [],
  'pesadas/7': DETALLE,
  'en-planta': [],
  'pendientes-aprobacion': [],
  'aprobadas-pendientes': [],
  completadas: [pesada({ id: 7, numero_ticket: 'TK-000007', estado: 'completado' })],
}

let llamadas: Llamada[] = []

beforeEach(() => {
  llamadas = instalarBackendFalso(POR_RUTA)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function props(nivel = 2) {
  return {
    sesion: sesionDe(nivel),
    onCerrarSesion: vi.fn(),
    pagina: 'tablero' as const,
    onCambiarPagina: vi.fn(),
    tema: 'claro' as const,
    onAlternarTema: vi.fn(),
  }
}

async function abrirDetalle(nivel = 2) {
  render(<Dashboard {...props(nivel)} />)
  const boton = await screen.findByRole('button', { name: 'Ver detalle del ticket TK-000007' })
  boton.focus()
  fireEvent.click(boton)
  const panel = await screen.findByRole('dialog', { name: 'Ticket TK-000007' })
  await within(panel).findByText('Recorrido')
  return { panel: within(panel), boton }
}

describe('Detalle de una pesada', () => {
  it('se abre al hacer clic en el ticket y pide la pesada completa', async () => {
    const { panel } = await abrirDetalle()

    expect(llamadas.some((l) => l.url.endsWith('/api/v1/pesadas/7'))).toBe(true)
    expect(screen.getByRole('dialog').getAttribute('aria-modal')).toBe('true')
    // Encabezado
    expect(panel.getByText('Completada')).toBeDefined()
    expect(panel.getByText('Peso manual')).toBeDefined()
    // Pesos, incluido el tercer pesaje y su diferencia con el bruto
    // El neto sale en Pesos y en la etapa de pre-pesaje del recorrido.
    expect(panel.getAllByText('15.000 kg')).toHaveLength(2)
    expect(panel.getAllByText('25.040 kg').length).toBeGreaterThan(0)
    expect(panel.getByText('+40 kg (+0.16 %)')).toBeDefined()
    // Datos
    expect(panel.getByText('José Pérez · V-12345678')).toBeDefined()
    expect(panel.getByText('Transportes Carabobo (T01)')).toBeDefined()
    expect(panel.getByText('Farmatodo (C01)')).toBeDefined()
    expect(panel.getByText('Valencia')).toBeDefined()
    expect(panel.getByText('Llegó con lona rota')).toBeDefined()
    // Recorrido, con quién hizo cada etapa
    expect(panel.getByText('Aprobada por Costos')).toBeDefined()
    expect(panel.getByText('Por: Carla Costos')).toBeDefined()
    expect(panel.getByText('Peso final y salida')).toBeDefined()
  })

  it('también se abre con un clic en cualquier parte de la fila', async () => {
    render(<Dashboard {...props()} />)
    const boton = await screen.findByRole('button', { name: 'Ver detalle del ticket TK-000007' })
    fireEvent.click(boton.closest('tr')!.querySelectorAll('td')[1])
    expect(await screen.findByRole('dialog')).toBeDefined()
  })

  it('arranca con el foco adentro, Escape lo cierra y el foco vuelve al ticket', async () => {
    const { boton } = await abrirDetalle()

    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cerrar detalle' }))
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(boton)
  })

  it('el botón Cerrar lo cierra', async () => {
    await abrirDetalle()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar detalle' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('con permiso de reportes ofrece el ticket PDF', async () => {
    const { panel } = await abrirDetalle(3)
    expect(panel.getByRole('button', { name: 'Ver ticket PDF' })).toBeDefined()
  })

  it('Centro de Costos (nivel 4) no ve el botón del ticket PDF', async () => {
    const { panel } = await abrirDetalle(4)
    expect(panel.queryByRole('button', { name: 'Ver ticket PDF' })).toBeNull()
  })

  it('el ticket PDF se pide con el token y se abre en otra pestaña', async () => {
    const pestana = { location: { href: '' }, close: vi.fn() }
    vi.stubGlobal('open', vi.fn(() => pestana))
    const crear = vi.fn(() => 'blob:ticket')
    URL.createObjectURL = crear
    URL.revokeObjectURL = vi.fn()

    const { panel } = await abrirDetalle()
    fireEvent.click(panel.getByRole('button', { name: 'Ver ticket PDF' }))

    await vi.waitFor(() => expect(pestana.location.href).toBe('blob:ticket'))
    const pedido = llamadas.find((l) => l.url.includes('/reportes/ticket/7.pdf'))
    expect(new Headers(pedido?.opciones?.headers).get('Authorization')).toBe('Bearer token-de-prueba')
  })

  it('si el detalle falla, lo dice y deja reintentar', async () => {
    llamadas = instalarBackendFalso({ ...POR_RUTA, 'pesadas/7': () => ({ status: 500, cuerpo: {} }) })
    render(<Dashboard {...props()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Ver detalle del ticket TK-000007' }))

    const panel = within(await screen.findByRole('dialog'))
    expect(await panel.findByText('El servidor respondió 500.')).toBeDefined()
    expect(panel.getByRole('button', { name: 'Reintentar' })).toBeDefined()
  })
})
