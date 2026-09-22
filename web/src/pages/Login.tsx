import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ErrorLogin, iniciarSesion } from '../api/auth'
import { IconoBalanza } from '../components/IconoBalanza'
import { Punto } from '../components/Punto'
import type { Sesion } from '../types/auth'

const estiloCampo =
  'h-5 w-full rounded-control border border-borde bg-fondo px-2 text-texto ' +
  'outline-none transition-colors focus:border-acento'
const estiloEtiqueta = 'font-semibold text-muted'

export function Login({ onIngreso }: { onIngreso: (sesion: Sesion) => void }) {
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const campoClave = useRef<HTMLInputElement>(null)

  // Después de un error, volver a la contraseña (el usuario casi nunca
  // es lo que está mal y no hace falta retipearlo).
  useEffect(() => {
    if (error) campoClave.current?.focus()
  }, [error])

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      onIngreso(await iniciarSesion(usuario.trim(), clave))
    } catch (e) {
      setError(e instanceof ErrorLogin ? e.message : 'Ocurrió un error inesperado.')
      setClave('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-3">
      <div className="flex items-center gap-2">
        <IconoBalanza className="size-5 text-texto" />
        <div>
          <p className="text-titulo font-bold">Romana</p>
          <p className="text-muted">Supervisión en vivo de pesaje de camiones</p>
        </div>
      </div>

      <div className="flex w-full max-w-50 flex-col gap-3 rounded-card border border-borde bg-card p-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-titulo font-bold">Iniciar sesión</h1>
          <p className="text-muted">Vista de supervisión — solo lectura</p>
        </div>

        <form onSubmit={enviar} className="flex flex-col gap-2" noValidate>
          <div className="flex flex-col gap-1">
            <label htmlFor="usuario" className={estiloEtiqueta}>
              Usuario
            </label>
            <input
              id="usuario"
              autoComplete="username"
              autoFocus
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              className={estiloCampo}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="clave" className={estiloEtiqueta}>
              Contraseña
            </label>
            <input
              id="clave"
              ref={campoClave}
              type="password"
              autoComplete="current-password"
              value={clave}
              onChange={(e) => setClave(e.target.value)}
              className={estiloCampo}
            />
          </div>

          {error && (
            <p
              role="alert"
              className="flex items-center gap-1 rounded-control border border-error px-2 py-1"
            >
              <Punto color="bg-error" />
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando || !usuario.trim() || !clave}
            className="mt-1 h-6 w-full rounded-control bg-acento font-semibold text-blanco transition-colors hover:bg-acento-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {enviando ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>
      </div>

      <p className="text-muted">Sura de Venezuela, C.A.</p>
    </main>
  )
}
