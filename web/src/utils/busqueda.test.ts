import { describe, expect, it } from 'vitest'
import { coincide, normalizar } from './busqueda'

describe('buscador de maestros', () => {
  it('ignora mayúsculas y tildes', () => {
    expect(normalizar('  JOSÉ Pérez Camión ')).toBe('jose perez camion')
    expect(coincide(['José Pérez'], 'jose PEREZ')).toBe(true)
    expect(coincide(['Jose Perez'], 'josé')).toBe(true)
  })

  it('busca en cualquiera de los valores, por coincidencia parcial', () => {
    expect(coincide(['ABC-123', 'Volvo FH'], 'volvo')).toBe(true)
    expect(coincide(['ABC-123', 'Volvo FH'], 'c-12')).toBe(true)
    expect(coincide(['ABC-123', 'Volvo FH'], 'scania')).toBe(false)
  })

  it('una búsqueda vacía o de espacios no filtra nada', () => {
    expect(coincide(['ABC-123'], '')).toBe(true)
    expect(coincide(['ABC-123'], '   ')).toBe(true)
  })
})
