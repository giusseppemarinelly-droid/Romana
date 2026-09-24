import type { RespuestaLogin, Sesion } from '../types/auth'

// Administrador (1), Supervisor (2) y Centro de Costos (4, para aprobar
// desde la web sin abrir la app de escritorio) -- ver
// services/auth_service.py. El Operador de Romana (3) trabaja en la
// estación de la báscula, no acá. El backend igual protege cada endpoint
// por su cuenta; esto es para darle un mensaje claro en vez de pantallas
// vacías o errores 403.
const NIVELES_PERMITIDOS = [1, 2, 4]

export class ErrorLogin extends Error {}

/**
 * Único request no-GET que hace la web (autenticación, no datos del
 * negocio). Ver Boundaries en docs/SPEC-web-supervision.md.
 */
export async function iniciarSesion(username: string, password: string): Promise<Sesion> {
  let respuesta: Response
  try {
    respuesta = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
  } catch {
    throw new ErrorLogin('No se pudo conectar con el servidor.')
  }

  if (!respuesta.ok) {
    throw new ErrorLogin(await leerDetalleError(respuesta))
  }

  const datos = (await respuesta.json()) as RespuestaLogin
  if (!NIVELES_PERMITIDOS.includes(datos.usuario.nivel)) {
    throw new ErrorLogin('Esta vista es para Administradores, Supervisores y Centro de Costos. El Operador de Romana trabaja desde la estación de la báscula.')
  }

  return {
    token: datos.access_token,
    usuario: datos.usuario,
    nivelNombre: datos.nivel_nombre,
    expiraEn: leerExpiracionJwt(datos.access_token),
  }
}

/**
 * El backend responde los errores de login como {"detail": "..."} con
 * un mensaje ya pensado para mostrarse (y deliberadamente genérico --
 * mismo texto para usuario inexistente y contraseña mala, ver hallazgo
 * I-09). Se muestra tal cual, sin reinterpretarlo.
 */
async function leerDetalleError(respuesta: Response): Promise<string> {
  try {
    const cuerpo = (await respuesta.json()) as { detail?: unknown }
    if (typeof cuerpo.detail === 'string') return cuerpo.detail
  } catch {
    // cuerpo no-JSON (ej. página de error de un proxy) -- cae al genérico
  }
  return `El servidor respondió con un error (${respuesta.status}).`
}

/**
 * Epoch en ms del claim `exp`. Solo lee el payload, no verifica la
 * firma -- eso lo hace el backend en cada request; acá es únicamente
 * para saber cuándo mostrar de nuevo el login. Si no se puede leer,
 * devuelve 0 (se trata como vencido).
 */
export function leerExpiracionJwt(token: string): number {
  try {
    const payload = token.split('.')[1]
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(base64)) as { exp?: unknown }
    return typeof exp === 'number' ? exp * 1000 : 0
  } catch {
    return 0
  }
}
