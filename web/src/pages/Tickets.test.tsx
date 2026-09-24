import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { instalarBackendFalso, pesada, sesionDe, type Llamada } from '../pruebas'
import { aFechaLocal } from '../utils/fechas'
import { Tickets } from './Tickets'

const HISTORIAL = [
  pesada({
    id: 11,
    numero_ticket: 'TK-000011',
    estado: 'completado',
    peso_neto: 15_000,
    vehiculo: { placa: 'AB1-23C', descripcion: null },
    producto: { codigo: '001', nombre: 'Harina de Maíz' },
  }),
  pesada({
    id: 12,
    numero_ticket: 'TK-000012',
    estado: 'completado',
    peso_neto: 5_000,
    vehiculo: { placa: 'XY9-87Z', descripcion: null },
    producto: null,
    empresa_cliente_proveedor: 'Distribuidora Guacara',
  }),
  pesada({ id: 13, numero_ticket: 'TK-000013', estado: 'anulado', vehiculo: { placa: 'QQQ-111', descripcion: null } }),
]

let llamadas: Llamada[] = []

beforeEach(() => {
  llamadas = instalarBackendFalso({
    'kardex/buscar': HISTORIAL,
    'pesadas/11': HISTORIAL[0],
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const props = {
  sesion: sesionDe(2),
  onCerrarSesion: vi.fn(),
  pagina: 'tickets' as const,
  onCambiarPagina: vi.fn(),
  tema: 'claro' as const,
  onAlternarTema: vi.fn(),
}

const pedidosKardex = () => llamadas.filter((l) => l.url.includes('kardex/buscar'))
const parametros = (l: Llamada) => new URL(l.url, 'http://x').searchParams

describe('Tickets', () => {
  it('por defecto pide los últimos 7 días, todos los estados', async () => {
    render(<Tickets {...props} />)
    await screen.findByText('TK-000011')

    expect(pedidosKardex()).toHaveLength(1)
    const p = parametros(pedidosKardex()[0])
    const hoy = new Date()
    const hace6 = new Date()
    hace6.setDate(hoy.getDate() - 6)
    expect(p.get('fecha_inicio')).toBe(`${aFechaLocal(hace6)}T00:00:00`)
    // Hasta el último instante del día: la comparación del backend es <=.
    expect(p.get('fecha_fin')).toBe(`${aFechaLocal(hoy)}T23:59:59.999999`)
    expect(p.get('estado')).toBeNull()
    expect(p.get('limit')).toBe('500')
  })

  it('muestra la tabla con estado y los KPIs del resultado', async () => {
    render(<Tickets {...props} />)
    await screen.findByText('TK-000011')

    const tabla = within(screen.getByRole('table'))
    expect(tabla.getByText('Anulada')).toBeDefined()
    expect(tabla.getByText('Distribuidora Guacara')).toBeDefined()
    expect(screen.getByText('20.000 kg')).toBeDefined() // neto de las 2 completadas
    expect(screen.getByText('0 en curso · 1 anulada')).toBeDefined()
  })

  it('el texto filtra en el navegador, sin volver a pedirle al backend', async () => {
    render(<Tickets {...props} />)
    await screen.findByText('TK-000011')
    const antes = llamadas.length

    const buscar = screen.getByRole('searchbox')
    // Sin tilde también encuentra "Maíz".
    fireEvent.change(buscar, { target: { value: 'maiz' } })
    expect(screen.getByText('TK-000011')).toBeDefined()
    expect(screen.queryByText('TK-000012')).toBeNull()

    // Por placa
    fireEvent.change(buscar, { target: { value: 'xy9' } })
    expect(screen.getByText('TK-000012')).toBeDefined()
    expect(screen.queryByText('TK-000011')).toBeNull()

    // Por empresa
    fireEvent.change(buscar, { target: { value: 'guacara' } })
    expect(screen.getByText('TK-000012')).toBeDefined()

    expect(llamadas.length).toBe(antes)
  })

  it('cambiar el estado vuelve a pedir al backend con ese filtro', async () => {
    render(<Tickets {...props} />)
    await screen.findByText('TK-000011')

    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'anulado' } })

    await vi.waitFor(() => expect(pedidosKardex()).toHaveLength(2))
    expect(parametros(pedidosKardex()[1]).get('estado')).toBe('anulado')
  })

  it('cambiar las fechas vuelve a pedir al backend con el nuevo rango', async () => {
    render(<Tickets {...props} />)
    await screen.findByText('TK-000011')

    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-09-01' } })
    await vi.waitFor(() => expect(pedidosKardex()).toHaveLength(2))
    expect(parametros(pedidosKardex()[1]).get('fecha_inicio')).toBe('2026-09-01T00:00:00')
    expect(await screen.findByText('TK-000011')).toBeDefined()
  })

  it('con Desde posterior a Hasta avisa y no le pide nada al backend', async () => {
    render(<Tickets {...props} />)
    await screen.findByText('TK-000011')

    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2099-01-01' } })
    expect(await screen.findByText(/posterior a Hasta/)).toBeDefined()
    expect(await screen.findByText('No hay pesadas para estos filtros.')).toBeDefined()
    expect(pedidosKardex()).toHaveLength(1)
  })

  it('si el resultado llega al tope, lo avisa', async () => {
    const muchas = Array.from({ length: 500 }, (_, i) => pesada({ id: 1000 + i, numero_ticket: `TK-${i}` }))
    instalarBackendFalso({ 'kardex/buscar': muchas })
    render(<Tickets {...props} />)

    expect(await screen.findByText(/solo las 500 pesadas más recientes/)).toBeDefined()
  })

  it('un clic en el ticket abre el detalle', async () => {
    render(<Tickets {...props} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Ver detalle del ticket TK-000011' }))

    const panel = within(await screen.findByRole('dialog', { name: 'Ticket TK-000011' }))
    expect(await panel.findByText('Recorrido')).toBeDefined()
  })
})
