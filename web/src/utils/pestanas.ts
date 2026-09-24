/**
 * Ids que enlazan cada pestaña con su panel (aria-controls /
 * aria-labelledby). Aparte del componente para que la pantalla que dibuja
 * los paneles arme exactamente los mismos.
 */
export function idsPestana(base: string, clave: string) {
  return { pestana: `${base}-pestana-${clave}`, panel: `${base}-panel-${clave}` }
}
