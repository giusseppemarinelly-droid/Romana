// Refleja 1:1 backend/schemas/auth.py -- si el backend agrega o cambia
// un campo, actualizar acá a mano (sin generación automática, ver spec).

export interface Usuario {
  id: number
  username: string
  nombre_completo: string
  nivel: number
  activo: boolean
  last_login: string | null
}

export interface RespuestaLogin {
  access_token: string
  token_type: string
  usuario: Usuario
  nivel_nombre: string
}

/** Lo que la web guarda después de un login exitoso. */
export interface Sesion {
  token: string
  usuario: Usuario
  nivelNombre: string
  /** Epoch en milisegundos, tomado del claim `exp` del JWT. */
  expiraEn: number
}
