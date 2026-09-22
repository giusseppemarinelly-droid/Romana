import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RespuestaLogin, Usuario } from '../types/auth'
import { ErrorLogin, iniciarSesion, leerExpiracionJwt } from './auth'

function base64url(texto: string): string {
  return btoa(texto).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function jwtFalso(payload: object): string {
  return [base64url('{"alg":"HS256"}'), base64url(JSON.stringify(payload)), 'firma'].join('.')
}

function usuario(nivel: number): Usuario {
  return {
    id: 7,
    username: 'usuario',
    nombre_completo: 'Usuario de Prueba',
    nivel,
    activo: true,
    last_login: null,
  }
}

function respuestaOk(nivel: number, exp = 2_000_000_000): Response {
  const cuerpo: RespuestaLogin = {
    access_token: jwtFalso({ sub: '7', nivel, exp }),
    token_type: 'bearer',
    usuario: usuario(nivel),
    nivel_nombre: nivel === 1 ? 'Administrador' : 'Supervisor',
  }
  return new Response(JSON.stringify(cuerpo), { status: 200 })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('iniciarSesion', () => {
  it('manda POST con JSON a /api/v1/auth/login', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(respuestaOk(1))
    vi.stubGlobal('fetch', fetchFalso)

    await iniciarSesion('admin', 'admin123')

    expect(fetchFalso).toHaveBeenCalledWith('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' }),
    })
  })

  it('devuelve la sesión para Administrador, con el vencimiento tomado del JWT', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuestaOk(1, 1_800_000_000)))

    const sesion = await iniciarSesion('admin', 'admin123')

    expect(sesion.usuario.nivel).toBe(1)
    expect(sesion.nivelNombre).toBe('Administrador')
    expect(sesion.expiraEn).toBe(1_800_000_000 * 1000)
  })

  it('acepta Supervisor (nivel 2)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuestaOk(2)))

    await expect(iniciarSesion('supervisor', 'super123')).resolves.toMatchObject({
      usuario: { nivel: 2 },
    })
  })

  it.each([3, 4])('rechaza nivel %i aunque el backend haya aceptado las credenciales', async (nivel) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuestaOk(nivel)))

    await expect(iniciarSesion('operador', 'oper123')).rejects.toThrow(
      'Esta vista es solo para Administradores y Supervisores.',
    )
  })

  it('muestra el mensaje del backend tal cual (sin inventar uno propio)', async () => {
    const detalle = 'Usuario o contraseña incorrectos'
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: detalle }), { status: 401 })),
    )

    await expect(iniciarSesion('x', 'y')).rejects.toThrow(detalle)
  })

  it('avisa si no hay conexión con el servidor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(iniciarSesion('admin', 'admin123')).rejects.toThrow(
      'No se pudo conectar con el servidor.',
    )
  })

  it('no revienta si el error no viene en JSON (ej. proxy caído)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<html>Bad Gateway</html>', { status: 502 })),
    )

    const error = await iniciarSesion('admin', 'admin123').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ErrorLogin)
    expect((error as Error).message).toBe('El servidor respondió con un error (502).')
  })
})

describe('leerExpiracionJwt', () => {
  it('decodifica base64url (con - y _), no solo base64 común', () => {
    // "???>>>" en base64 produce '/' y '+', que en base64url son '_' y '-'.
    const token = jwtFalso({ exp: 1_900_000_000, relleno: '???>>>???>>>' })
    expect(token.split('.')[1]).toMatch(/[-_]/)

    expect(leerExpiracionJwt(token)).toBe(1_900_000_000 * 1000)
  })

  it('devuelve 0 (vencido) si el token no se puede leer', () => {
    expect(leerExpiracionJwt('no-es-un-jwt')).toBe(0)
  })
})
