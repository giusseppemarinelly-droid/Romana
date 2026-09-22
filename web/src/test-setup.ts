import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Testing Library solo limpia el DOM sola cuando Vitest corre con
// `globals: true`; acá los tests importan todo explícitamente, así que
// hay que desmontar a mano -- si no, cada test ve también lo que
// renderizó el anterior.
afterEach(cleanup)
