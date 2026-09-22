import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useTema } from './useTema'

beforeEach(() => {
  localStorage.clear()
  delete document.documentElement.dataset.tema
})

describe('useTema', () => {
  it('arranca en claro (la paleta de escritorio) si nunca se eligió otro', () => {
    const { result } = renderHook(() => useTema())
    expect(result.current.tema).toBe('claro')
    expect(document.documentElement.dataset.tema).toBe('claro')
  })

  it('alterna a oscuro y lo recuerda para la próxima visita', () => {
    const { result, unmount } = renderHook(() => useTema())
    act(() => result.current.alternar())

    expect(document.documentElement.dataset.tema).toBe('oscuro')
    unmount()
    expect(renderHook(() => useTema()).result.current.tema).toBe('oscuro')
  })
})
