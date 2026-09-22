import { afterEach, describe, expect, it } from 'vitest'
import type { Sesion } from '../types/auth'
import { borrarSesion, guardarSesion, leerSesion } from './useSesion'

function sesion(expiraEn: number): Sesion {
  return {
    token: 'token',
    usuario: {
      id: 1,
      username: 'admin',
      nombre_completo: 'Administrador del Sistema',
      nivel: 1,
      activo: true,
      last_login: null,
    },
    nivelNombre: 'Administrador',
    expiraEn,
  }
}

afterEach(() => {
  sessionStorage.clear()
})

describe('sesión guardada en el navegador', () => {
  it('guarda y vuelve a leer la misma sesión', () => {
    const s = sesion(Date.now() + 60_000)
    guardarSesion(s)

    expect(leerSesion()).toEqual(s)
  })

  it('usa sessionStorage, no localStorage (se pierde al cerrar la pestaña)', () => {
    guardarSesion(sesion(Date.now() + 60_000))

    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(1)
  })

  it('descarta y borra una sesión vencida', () => {
    guardarSesion(sesion(Date.now() - 1))

    expect(leerSesion()).toBeNull()
    expect(sessionStorage.length).toBe(0)
  })

  it('descarta datos corruptos en vez de romper la app', () => {
    sessionStorage.setItem('romana.sesion', '{esto no es json')

    expect(leerSesion()).toBeNull()
    expect(sessionStorage.length).toBe(0)
  })

  it('borrarSesion deja el navegador sin sesión', () => {
    guardarSesion(sesion(Date.now() + 60_000))
    borrarSesion()

    expect(leerSesion()).toBeNull()
  })
})
