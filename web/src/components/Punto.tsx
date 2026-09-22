/** Punto de color de 8px. Siempre acompaña a un texto, nunca lo reemplaza. */
export function Punto({ color }: { color: string }) {
  return <span className={`size-1 shrink-0 rounded-full ${color}`} aria-hidden="true" />
}
