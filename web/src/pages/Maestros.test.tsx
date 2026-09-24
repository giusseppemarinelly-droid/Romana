import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { instalarBackendFalso, sesionDe, type Llamada } from '../pruebas'
import type { Conductor, Empresa, Vehiculo } from '../types/maestros'
import { Maestros } from './Maestros'

const vehiculo = (v: Partial<Vehiculo>): Vehiculo => ({
  id: 1,
  placa: 'ABC-123',
  descripcion: 'Volvo FH',
  tara_registrada: 14_500,
  tipo: 'camion',
  proveedor_id: null,
  activo: true,
  ...v,
})

const conductor = (c: Partial<Conductor>): Conductor => ({
  id: 1,
  nombre: 'José Pérez',
  documento: 'V-12345678',
  tipo_documento: 'cedula',
  telefono: null,
  activo: true,
  ...c,
})

const empresa = (e: Partial<Empresa>): Empresa => ({
  id: 1,
  codigo: 'P001',
  nombre: 'Farmatodo',
  rif: 'J-00000000-1',
  direccion: null,
  telefono: null,
  email: null,
  activo: true,
  ...e,
})

// El backend lista solo activos por defecto: la pantalla pide las dos
// mitades (activo=true / activo=false). Las claves con "activo=false" van
// primero porque el backend falso se queda con la primera que matchea.
const POR_RUTA: Record<string, unknown> = {
  '/vehiculos?activo=false': [vehiculo({ id: 3, placa: 'ZZZ-999', descripcion: 'De baja', activo: false })],
  '/vehiculos?activo=true': [
    vehiculo({ id: 1, placa: 'ABC-123', descripcion: 'Volvo FH' }),
    vehiculo({ id: 2, placa: 'MNO-456', descripcion: 'Camión Mercedes', tipo: 'cisterna' }),
  ],
  '/conductores?activo=false': [],
  '/conductores?activo=true': [conductor({ id: 1, nombre: 'JOSÉ PÉREZ' })],
  '/proveedores?activo=false': [],
  '/proveedores?activo=true': [empresa({ id: 1, nombre: 'Farmatodo' })],
  '/empresas_transportistas?activo=false': [],
  '/empresas_transportistas?activo=true': [empresa({ id: 1, codigo: 'T01', nombre: 'Transportes Carabobo' })],
}

let llamadas: Llamada[] = []

beforeEach(() => {
  llamadas = instalarBackendFalso(POR_RUTA)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const props = {
  sesion: sesionDe(2),
  onCerrarSesion: vi.fn(),
  pagina: 'maestros' as const,
  onCambiarPagina: vi.fn(),
  tema: 'claro' as const,
  onAlternarTema: vi.fn(),
}

/** Rutas de API pedidas, sin el prefijo ni la query. */
const rutasPedidas = () =>
  llamadas.map(({ url }) => url.replace('/api/v1', '').split('?')[0])

const panelVisible = () => screen.getByRole('tabpanel')

describe('Maestros', () => {
  it('al entrar muestra los vehículos, activos e inactivos, y pide solo ese catálogo', async () => {
    render(<Maestros {...props} />)

    expect(await screen.findByText('ABC-123')).toBeDefined()
    expect(screen.getByText('MNO-456')).toBeDefined()
    expect(screen.getByText('Cisterna')).toBeDefined()
    expect(screen.getAllByText('14.500')).toHaveLength(3)
    // El dado de baja aparece, marcado como inactivo.
    const baja = screen.getByText('ZZZ-999').closest('tr')!
    expect(within(baja).getByText('Inactivo')).toBeDefined()
    expect(screen.getByText('3 de 3 vehículos')).toBeDefined()

    expect(screen.getByRole('tab', { name: 'Vehículos' }).getAttribute('aria-selected')).toBe('true')
    expect(new Set(rutasPedidas())).toEqual(new Set(['/vehiculos']))
  })

  it('cambiar de pestaña pide solo esa ruta, y volver a una ya vista no pide nada', async () => {
    render(<Maestros {...props} />)
    await screen.findByText('ABC-123')
    const antes = llamadas.length

    fireEvent.click(screen.getByRole('tab', { name: 'Choferes' }))
    expect(await within(panelVisible()).findByText('JOSÉ PÉREZ')).toBeDefined()
    expect(within(panelVisible()).getByText('Cédula')).toBeDefined()
    expect(new Set(rutasPedidas().slice(antes))).toEqual(new Set(['/conductores']))

    const conChoferes = llamadas.length
    fireEvent.click(screen.getByRole('tab', { name: 'Vehículos' }))
    expect(within(panelVisible()).getByText('ABC-123')).toBeDefined()
    fireEvent.click(screen.getByRole('tab', { name: 'Choferes' }))
    expect(within(panelVisible()).getByText('JOSÉ PÉREZ')).toBeDefined()
    expect(llamadas.length).toBe(conChoferes)
  })

  it('el buscador filtra sin tildes ni mayúsculas y sin volver a pedir', async () => {
    render(<Maestros {...props} />)
    await screen.findByText('ABC-123')
    const antes = llamadas.length
    const buscador = screen.getByRole('searchbox')

    // Mayúsculas contra "Camión Mercedes"; después, sin tilde contra con tilde.
    fireEvent.change(buscador, { target: { value: 'MERCEDES' } })
    expect(screen.getByText('MNO-456')).toBeDefined()
    expect(screen.queryByText('ABC-123')).toBeNull()
    expect(screen.getByText('1 de 3 vehículos')).toBeDefined()

    fireEvent.change(buscador, { target: { value: 'camion merc' } })
    expect(screen.getByText('1 de 3 vehículos')).toBeDefined()

    fireEvent.change(buscador, { target: { value: 'scania' } })
    expect(screen.getByText('Ningún resultado para «scania».')).toBeDefined()
    expect(screen.getByText('0 de 3 vehículos')).toBeDefined()

    // En choferes, "jose perez" encuentra "JOSÉ PÉREZ".
    fireEvent.click(screen.getByRole('tab', { name: 'Choferes' }))
    await within(panelVisible()).findByText('JOSÉ PÉREZ')
    const antesChoferes = llamadas.length
    fireEvent.change(within(panelVisible()).getByRole('searchbox'), {
      target: { value: 'jose perez' },
    })
    expect(within(panelVisible()).getByText('JOSÉ PÉREZ')).toBeDefined()
    expect(within(panelVisible()).getByText('1 de 1 choferes')).toBeDefined()

    // Solo el cambio de pestaña pidió algo; escribir, nunca.
    expect(rutasPedidas().slice(antes, antesChoferes).every((r) => r === '/conductores')).toBe(true)
    expect(llamadas.length).toBe(antesChoferes)
  })

  it('las flechas se mueven entre pestañas y dan la vuelta en los extremos', async () => {
    render(<Maestros {...props} />)
    await screen.findByText('ABC-123')
    const vehiculos = screen.getByRole('tab', { name: 'Vehículos' })

    // Solo la activa entra en el orden de Tab.
    expect(vehiculos.tabIndex).toBe(0)
    expect(screen.getByRole('tab', { name: 'Choferes' }).tabIndex).toBe(-1)

    fireEvent.keyDown(vehiculos, { key: 'ArrowRight' })
    const choferes = screen.getByRole('tab', { name: 'Choferes' })
    expect(choferes.getAttribute('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(choferes)

    fireEvent.keyDown(choferes, { key: 'ArrowLeft' })
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Vehículos' }), { key: 'ArrowLeft' })
    const transportistas = screen.getByRole('tab', { name: 'Transportistas' })
    expect(transportistas.getAttribute('aria-selected')).toBe('true')
    expect(await within(panelVisible()).findByText('Transportes Carabobo')).toBeDefined()

    // El panel visible está enlazado con su pestaña.
    expect(panelVisible().getAttribute('aria-labelledby')).toBe(transportistas.id)
    expect(transportistas.getAttribute('aria-controls')).toBe(panelVisible().id)
  })

  it('si falla la carga muestra el error y Reintentar vuelve a pedir', async () => {
    let fallar = true
    llamadas = instalarBackendFalso({
      '/vehiculos': () =>
        fallar ? { status: 500, cuerpo: {} } : { status: 200, cuerpo: [vehiculo({})] },
    })
    render(<Maestros {...props} />)

    expect(await screen.findByRole('alert')).toBeDefined()
    fallar = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    // Las dos mitades (activos/inactivos) devuelven el mismo vehículo en este doble.
    expect((await screen.findAllByText('ABC-123')).length).toBeGreaterThan(0)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('un catálogo vacío lo dice en vez de mostrar una tabla vacía', async () => {
    llamadas = instalarBackendFalso({ '/vehiculos': [] })
    render(<Maestros {...props} />)

    expect(await screen.findByText('No hay vehículos registrados.')).toBeDefined()
    expect(screen.getByText('0 de 0 vehículos')).toBeDefined()
  })

  it('solo hace lecturas: ningún request con método de escritura', async () => {
    render(<Maestros {...props} />)
    await screen.findByText('ABC-123')
    for (const clave of ['Choferes', 'Proveedores', 'Transportistas']) {
      fireEvent.click(screen.getByRole('tab', { name: clave }))
    }
    await within(panelVisible()).findByText('Transportes Carabobo')

    expect(new Set(rutasPedidas())).toEqual(
      new Set(['/vehiculos', '/conductores', '/proveedores', '/empresas_transportistas']),
    )
    for (const { opciones } of llamadas) {
      expect(opciones?.method ?? 'GET').toBe('GET')
    }
  })
})
