import { describe, expect, it } from 'vitest'

// Guardia de la escala cerrada (ver index.css → @theme). Tailwind ya no
// genera CSS para colores/tamaños/radios fuera de la lista, pero los
// valores "a mano" -- un hex suelto, un text-[13px], un p-1.5 -- sí
// pasarían. Esto los atrapa antes de que lleguen a la pantalla.

const fuentes = import.meta.glob(['./**/*.tsx', '!./**/*.test.tsx'], {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

function buscar(patron: RegExp) {
  return Object.entries(fuentes).flatMap(([archivo, codigo]) =>
    [...codigo.matchAll(patron)].map((m) => `${archivo}: ${m[0]}`),
  )
}

describe('sistema de diseño', () => {
  it('encontró los componentes (si no, esta guardia no revisa nada)', () => {
    expect(Object.keys(fuentes).length).toBeGreaterThan(10)
  })

  it('ningún color hex fuera de src/tema.ts e index.css', () => {
    expect(buscar(/#[0-9a-fA-F]{6}\b/g)).toEqual([])
  })

  it('ningún valor arbitrario de Tailwind (text-[13px], p-[27px]...)', () => {
    expect(buscar(/\b[a-z-]+-\[[^\]]+\]/g)).toEqual([])
  })

  it('ningún espaciado fraccionario: la unidad es 8px, p-0.5 serían 4px', () => {
    expect(buscar(/\b-?[a-z]+-\d+\.5\b/g)).toEqual([])
  })

  it('sin sombras', () => {
    expect(buscar(/\bshadow(-\w+)?\b/g)).toEqual([])
  })
})
