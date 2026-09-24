// Fechas del historial. Se trabaja en hora LOCAL a propósito: el backend
// guarda las fechas con datetime.now() del servidor de planta, sin zona,
// y el navegador del supervisor está en esa misma planta.

/** Date -> "2026-09-24" en hora local (toISOString() la pasaría a UTC). */
export function aFechaLocal(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const dia = String(fecha.getDate()).padStart(2, '0')
  return `${fecha.getFullYear()}-${mes}-${dia}`
}

/** Los últimos `dias` días, hoy incluido: 7 -> de hace 6 días a hoy. */
export function ultimosDias(dias: number, hoy: Date = new Date()): { desde: string; hasta: string } {
  const desde = new Date(hoy)
  desde.setDate(hoy.getDate() - (dias - 1))
  return { desde: aFechaLocal(desde), hasta: aFechaLocal(hoy) }
}

/** "24/09/2026 02:30 p. m." -- fecha y hora juntas, para el historial y el recorrido. */
export function fechaHora(fecha: string | null | undefined): string {
  if (!fecha) return '—'
  return new Date(fecha).toLocaleString('es-VE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}
