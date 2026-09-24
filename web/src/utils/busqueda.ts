/**
 * Texto comparable para el buscador: sin mayúsculas ni tildes, así
 * "jose" encuentra "JOSÉ" y "camion" encuentra "Camión" -- en planta se
 * escribe rápido y sin acentos.
 */
export function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim()
}

/** ¿Alguno de los valores contiene la búsqueda? Búsqueda vacía = todo coincide. */
export function coincide(valores: string[], busqueda: string): boolean {
  const buscado = normalizar(busqueda)
  if (!buscado) return true
  return valores.some((v) => normalizar(v).includes(buscado))
}
