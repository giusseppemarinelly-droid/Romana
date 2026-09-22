/**
 * "hace cuánto" en texto corto. Lo que un supervisor realmente mira en
 * el tablero no es la hora exacta sino hace cuánto que ese camión está
 * esperando en ese estado.
 */
export function tiempoTranscurrido(desde: string | null, ahora: Date = new Date()): string {
  if (!desde) return '—'

  const minutos = Math.floor((ahora.getTime() - new Date(desde).getTime()) / 60_000)
  // Negativo = el reloj del servidor va adelantado respecto al del
  // navegador; mostrar "recién" es más honesto que "hace -3 min".
  if (minutos < 1) return 'recién'
  if (minutos < 60) return `${minutos} min`

  const horas = Math.floor(minutos / 60)
  if (horas < 24) {
    const resto = minutos % 60
    return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`
  }

  const dias = Math.floor(horas / 24)
  return dias === 1 ? '1 día' : `${dias} días`
}

/** Minutos sueltos a texto legible: 135 -> "2 h 15 min". */
export function formatearMinutos(minutos: number | null): string {
  if (minutos === null) return '—'
  const total = Math.round(minutos)
  if (total < 60) return `${total} min`

  const horas = Math.floor(total / 60)
  const resto = total % 60
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`
}

/** "2026-09-22" -> "22/09", para los ejes de los gráficos. */
export function fechaCorta(fecha: string): string {
  const [, mes, dia] = fecha.split('-')
  return `${dia}/${mes}`
}

/** Hora del día en formato 12h, como el reloj de la app de escritorio. */
export function horaCorta(fecha: string | null): string {
  if (!fecha) return '—'
  return new Date(fecha).toLocaleTimeString('es-VE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}
