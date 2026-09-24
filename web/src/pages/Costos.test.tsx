import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { instalarBackendFalso, pesada, sesionDe, type Llamada } from '../pruebas'
import { Costos } from './Costos'

const PENDIENTE = pesada({
  id: 2,
  numero_ticket: 'TK-PENDIENTE',
  estado: 'pendiente_aprobacion',
  peso_neto: 10_000,
  peso_guia: 12_000,
})

const LECTURAS = {
  'pendientes-aprobacion': [PENDIENTE],
  'auto-aprobadas': [
    pesada({ id: 5, numero_ticket: 'TK-AUTO', auto_aprobado: true, peso_neto: 11_900, peso_guia: 12_000 }),
  ],
}

type Respuesta = (l: Llamada) => { status: number; cuerpo: unknown }

/** Backend con las lecturas de la pantalla más las respuestas a los POST. */
function backend(escrituras: Record<string, Respuesta> = {}) {
  // Las rutas de escritura primero: `instalarBackendFalso` usa la primera
  // clave contenida en la URL.
  return instalarBackendFalso({ ...escrituras, ...LECTURAS })
}

const OK: Respuesta = () => ({ status: 200, cuerpo: PENDIENTE })

let llamadas: Llamada[] = []

beforeEach(() => {
  llamadas = backend()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function propsDe(nivel: number) {
  return {
    sesion: sesionDe(nivel),
    onCerrarSesion: vi.fn(),
    pagina: 'costos' as const,
    onCambiarPagina: vi.fn(),
    tema: 'claro' as const,
    onAlternarTema: vi.fn(),
  }
}

const posts = () => llamadas.filter((l) => l.opciones?.method === 'POST')
const lecturasDeCola = () =>
  llamadas.filter((l) => l.url.includes('pendientes-aprobacion') && !l.opciones?.method)

async function abrir(boton: RegExp) {
  render(<Costos {...propsDe(4)} />)
  const abridor = await screen.findByRole('button', { name: boton })
  // fireEvent no mueve el foco como un clic real: se enfoca a mano para
  // poder verificar que al cerrar el diálogo vuelve a este botón.
  abridor.focus()
  fireEvent.click(abridor)
  return { abridor, dialogo: screen.getByRole('dialog') }
}

describe('Costos', () => {
  it('muestra la cola con la diferencia contra la guía ya calculada', async () => {
    render(<Costos {...propsDe(2)} />)

    // Una vez en la tabla y otra en la card "Más antigua en cola".
    expect(await screen.findAllByText('TK-PENDIENTE')).toHaveLength(2)
    // 10.000 vs guía 12.000 = 16,67% fuera de tolerancia
    expect(screen.getByText('16.67 %')).toBeDefined()
    expect(screen.getByText('TK-AUTO')).toBeDefined()
  })

  it.each([1, 2, 4])('nivel %i (con permiso centro_costos) ve Aprobar y Rechazar', async (nivel) => {
    render(<Costos {...propsDe(nivel)} />)

    expect(await screen.findByRole('button', { name: 'Aprobar TK-PENDIENTE' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Rechazar TK-PENDIENTE' })).toBeDefined()
    expect(screen.getByText(/se pueden aprobar o rechazar desde acá/i)).toBeDefined()
  })

  it('sin el permiso (nivel 3) sigue siendo de solo lectura', async () => {
    render(<Costos {...propsDe(3)} />)
    await screen.findAllByText('TK-PENDIENTE')

    const textos = screen.queryAllByRole('button').map((b) => b.textContent ?? '')
    expect(textos.some((t) => /aprobar|rechazar/i.test(t))).toBe(false)
    expect(screen.getByText(/vista de solo lectura/i)).toBeDefined()
  })

  it('aprobar pide confirmación con el resumen antes de mandar nada', async () => {
    const { dialogo } = await abrir(/aprobar TK-PENDIENTE/i)

    expect(dialogo.getAttribute('aria-modal')).toBe('true')
    expect(within(dialogo).getByRole('heading').textContent).toBe('Aprobar TK-PENDIENTE')
    expect(within(dialogo).getByText('ABC-123')).toBeDefined()
    expect(within(dialogo).getByText(/16\.67 %/)).toBeDefined()
    // El foco arranca adentro, en el comentario (opcional): ahí un Enter
    // de más es un salto de línea, no una aprobación.
    expect(document.activeElement).toBe(within(dialogo).getByLabelText(/Comentario \(opcional\)/))
    expect(posts()).toHaveLength(0)
  })

  it('confirmar la aprobación hace POST, cierra, avisa y recarga la cola', async () => {
    llamadas = backend({ '/aprobar': OK })
    const { dialogo, abridor } = await abrir(/aprobar TK-PENDIENTE/i)
    const lecturasAntes = lecturasDeCola().length

    fireEvent.click(within(dialogo).getByRole('button', { name: 'Aprobar' }))

    // Dentro de una región role="status" (hay otra, la de conexión en el
    // sidebar), para que el lector de pantalla lo anuncie.
    const aviso = await screen.findByText('TK-PENDIENTE aprobada')
    expect(aviso.closest('[role="status"]')).not.toBeNull()
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(abridor)

    expect(posts()).toHaveLength(1)
    expect(posts()[0].url).toBe('/api/v1/pesadas/2/aprobar')
    // Sin comentario: se aprueba igual, el backend guarda null.
    expect(JSON.parse(posts()[0].opciones?.body as string)).toEqual({ comentario: '' })
    await waitFor(() => expect(lecturasDeCola().length).toBeGreaterThan(lecturasAntes))
  })

  it('al aprobar se puede dejar un comentario de por qué', async () => {
    llamadas = backend({ '/aprobar': OK })
    const { dialogo } = await abrir(/aprobar TK-PENDIENTE/i)

    fireEvent.change(within(dialogo).getByLabelText(/Comentario \(opcional\)/), {
      target: { value: '  La guía venía sin las paletas.  ' },
    })
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Aprobar' }))

    await screen.findByText('TK-PENDIENTE aprobada')
    expect(JSON.parse(posts()[0].opciones?.body as string)).toEqual({
      comentario: 'La guía venía sin las paletas.',
    })
  })

  it('no manda dos veces aunque se haga doble clic', async () => {
    let responder: () => void = () => {}
    llamadas = backend({ '/aprobar': OK })
    // Retiene la respuesta para poder hacer el segundo clic "en vuelo".
    const fetchReal = globalThis.fetch
    const fetchRetenido = vi.fn((url: string, opciones?: RequestInit) =>
      opciones?.method === 'POST'
        ? new Promise<Response>((resolver) => {
            responder = () => resolver(fetchReal(url, opciones))
          })
        : fetchReal(url, opciones),
    )
    vi.stubGlobal('fetch', fetchRetenido)
    const { dialogo } = await abrir(/aprobar TK-PENDIENTE/i)

    const confirmar = within(dialogo).getByRole('button', { name: 'Aprobar' })
    fireEvent.click(confirmar)
    fireEvent.click(confirmar)

    expect(within(dialogo).getByRole('button', { name: 'Enviando…' })).toHaveProperty('disabled', true)
    expect(within(dialogo).getByRole('button', { name: 'Cancelar' })).toHaveProperty('disabled', true)
    await act(async () => responder())
    await screen.findByText('TK-PENDIENTE aprobada')
    // Cuenta los intentos de fetch (no solo los que llegaron a responder).
    expect(fetchRetenido.mock.calls.filter(([, o]) => o?.method === 'POST')).toHaveLength(1)
  })

  it('el rechazo exige motivo y lo manda en el cuerpo', async () => {
    llamadas = backend({ '/rechazar': OK })
    const { dialogo } = await abrir(/rechazar TK-PENDIENTE/i)

    const motivo = within(dialogo).getByRole('textbox', { name: /motivo del rechazo/i })
    expect(document.activeElement).toBe(motivo)
    const confirmar = within(dialogo).getByRole('button', { name: 'Rechazar' })
    expect(confirmar).toHaveProperty('disabled', true)

    // Solo espacios no cuenta como motivo.
    fireEvent.change(motivo, { target: { value: '    ' } })
    expect(confirmar).toHaveProperty('disabled', true)

    fireEvent.change(motivo, { target: { value: '  Faltan 3 bultos  ' } })
    expect(confirmar).toHaveProperty('disabled', false)
    fireEvent.click(confirmar)

    expect(await screen.findByText('TK-PENDIENTE rechazada')).toBeDefined()
    expect(posts()).toHaveLength(1)
    expect(posts()[0].url).toBe('/api/v1/pesadas/2/rechazar')
    expect(JSON.parse(String(posts()[0].opciones?.body))).toEqual({ motivo: 'Faltan 3 bultos' })
  })

  it('si el backend rechaza la decisión, muestra su mensaje y deja el diálogo abierto', async () => {
    llamadas = backend({
      '/aprobar': () => ({
        status: 400,
        cuerpo: { detail: "Solo se pueden aprobar pesadas en estado 'pendiente_aprobacion'." },
      }),
    })
    const { dialogo } = await abrir(/aprobar TK-PENDIENTE/i)

    fireEvent.click(within(dialogo).getByRole('button', { name: 'Aprobar' }))

    const alerta = await within(dialogo).findByRole('alert')
    expect(alerta.textContent).toContain("Solo se pueden aprobar pesadas en estado 'pendiente_aprobacion'.")
    expect(screen.getByRole('dialog')).toBeDefined()
    // Se puede reintentar: el botón vuelve a estar habilitado.
    expect(within(dialogo).getByRole('button', { name: 'Aprobar' })).toHaveProperty('disabled', false)
  })

  it('un 401 al decidir manda de vuelta al login', async () => {
    llamadas = backend({ '/aprobar': () => ({ status: 401, cuerpo: { detail: 'Token vencido' } }) })
    const props = propsDe(4)
    render(<Costos {...props} />)
    fireEvent.click(await screen.findByRole('button', { name: /aprobar TK-PENDIENTE/i }))

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Aprobar' }))

    await waitFor(() => expect(props.onCerrarSesion).toHaveBeenCalled())
  })

  it('Escape cierra el diálogo sin decidir y devuelve el foco', async () => {
    const { abridor } = await abrir(/rechazar TK-PENDIENTE/i)

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(abridor)
    expect(posts()).toHaveLength(0)
  })

  it('Tab no se escapa del diálogo', async () => {
    const { dialogo } = await abrir(/aprobar TK-PENDIENTE/i)
    // El primer enfocable ahora es el comentario, el último "Aprobar".
    const comentario = within(dialogo).getByLabelText(/Comentario \(opcional\)/)
    const confirmar = within(dialogo).getByRole('button', { name: 'Aprobar' })

    confirmar.focus()
    fireEvent.keyDown(confirmar, { key: 'Tab' })
    expect(document.activeElement).toBe(comentario)

    fireEvent.keyDown(comentario, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(confirmar)
  })
})

describe('Costos: detalle antes de decidir', () => {
  it('el ticket de la cola abre el detalle completo de la pesada', async () => {
    llamadas = backend({ '/pesadas/2': () => ({ status: 200, cuerpo: PENDIENTE }) })
    render(<Costos {...propsDe(4)} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Ver detalle del ticket TK-PENDIENTE' }))

    expect(screen.getByRole('dialog')).toBeDefined()
    await waitFor(() => expect(llamadas.some((l) => l.url.endsWith('/pesadas/2'))).toBe(true))
  })
})
