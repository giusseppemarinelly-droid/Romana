import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useWebSocket } from './useWebSocket'

/** WebSocket falso: registra las instancias creadas y deja dispararles eventos a mano. */
class WebSocketFalso {
  static instancias: WebSocketFalso[] = []
  static readonly CLOSED = 3
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  cerrado = false
  readonly url: string

  constructor(url: string) {
    this.url = url
    WebSocketFalso.instancias.push(this)
  }

  close() {
    this.cerrado = true
  }

  abrir() {
    this.onopen?.()
  }

  cortar() {
    this.onclose?.()
  }

  mandar(evento: object) {
    this.onmessage?.({ data: JSON.stringify(evento) })
  }
}

beforeEach(() => {
  WebSocketFalso.instancias = []
  vi.stubGlobal('WebSocket', WebSocketFalso)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('useWebSocket', () => {
  it('se conecta al endpoint del backend con el token en la URL', () => {
    renderHook(() => useWebSocket('un-token', vi.fn()))

    const url = WebSocketFalso.instancias[0].url
    expect(url).toContain('/ws/pesadas')
    expect(url).toContain('token=un-token')
    expect(url.startsWith('ws://') || url.startsWith('wss://')).toBe(true)
  })

  it('avisa de los eventos que manda el servidor', async () => {
    const alRecibir = vi.fn()
    renderHook(() => useWebSocket('t', alRecibir))

    act(() => WebSocketFalso.instancias[0].abrir())
    WebSocketFalso.instancias[0].mandar({ tipo: 'pesada_creada', pesada_id: 7 })

    expect(alRecibir).toHaveBeenCalledWith({ tipo: 'pesada_creada', pesada_id: 7 })
  })

  it('ignora mensajes que no son JSON en vez de romperse', () => {
    const alRecibir = vi.fn()
    renderHook(() => useWebSocket('t', alRecibir))

    act(() => WebSocketFalso.instancias[0].abrir())
    WebSocketFalso.instancias[0].onmessage?.({ data: 'esto no es json' })

    expect(alRecibir).not.toHaveBeenCalled()
  })

  it('reconecta con espera creciente y la corta al lograr conectarse', async () => {
    renderHook(() => useWebSocket('t', vi.fn()))
    expect(WebSocketFalso.instancias).toHaveLength(1)

    // Primer corte: reintenta al segundo.
    act(() => WebSocketFalso.instancias[0].cortar())
    await vi.advanceTimersByTimeAsync(999)
    expect(WebSocketFalso.instancias).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(WebSocketFalso.instancias).toHaveLength(2)

    // Segundo corte seguido: la espera se duplica (2s).
    act(() => WebSocketFalso.instancias[1].cortar())
    await vi.advanceTimersByTimeAsync(1999)
    expect(WebSocketFalso.instancias).toHaveLength(2)
    await vi.advanceTimersByTimeAsync(1)
    expect(WebSocketFalso.instancias).toHaveLength(3)

    // Conectó bien: la próxima caída vuelve a esperar 1s, no 4s.
    act(() => WebSocketFalso.instancias[2].abrir())
    act(() => WebSocketFalso.instancias[2].cortar())
    await vi.advanceTimersByTimeAsync(1000)
    expect(WebSocketFalso.instancias).toHaveLength(4)
  })

  it('no espera más de 30s entre reintentos', async () => {
    renderHook(() => useWebSocket('t', vi.fn()))

    for (let i = 0; i < 10; i++) {
      act(() => WebSocketFalso.instancias[WebSocketFalso.instancias.length - 1].cortar())
      await vi.advanceTimersByTimeAsync(30_000)
    }

    const antes = WebSocketFalso.instancias.length
    act(() => WebSocketFalso.instancias[antes - 1].cortar())
    await vi.advanceTimersByTimeAsync(30_000)
    expect(WebSocketFalso.instancias.length).toBe(antes + 1)
  })

  it('informa si está conectado, para poder avisar que los datos no son en vivo', () => {
    const { result } = renderHook(() => useWebSocket('t', vi.fn()))
    expect(result.current.conectado).toBe(false)

    act(() => WebSocketFalso.instancias[0].abrir())
    expect(result.current.conectado).toBe(true)

    act(() => WebSocketFalso.instancias[0].cortar())
    expect(result.current.conectado).toBe(false)
  })

  it('cierra la conexión y no reconecta al desmontar la pantalla', async () => {
    const { unmount } = renderHook(() => useWebSocket('t', vi.fn()))
    const ws = WebSocketFalso.instancias[0]

    unmount()
    expect(ws.cerrado).toBe(true)

    act(() => ws.cortar())
    await vi.advanceTimersByTimeAsync(60_000)
    expect(WebSocketFalso.instancias).toHaveLength(1)
  })

  it('no conecta si todavía no hay token', () => {
    renderHook(() => useWebSocket('', vi.fn()))
    expect(WebSocketFalso.instancias).toHaveLength(0)
  })
})
