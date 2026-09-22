// Los colores de src/index.css en valor crudo, para lo que no lee clases
// de Tailwind (Recharts). Si cambia uno allá, cambiarlo acá.

export type Tema = 'claro' | 'oscuro'

export interface Paleta {
  card: string
  acento: string
  exito: string
  advertencia: string
  texto: string
  muted: string
  borde: string
}

export const PALETAS: Record<Tema, Paleta> = {
  // Paleta de la app de escritorio (config.py → UI).
  claro: {
    card: '#FFFFFF',
    acento: '#C1802A',
    exito: '#1F7A4D',
    advertencia: '#B5461F',
    texto: '#211F1D',
    muted: '#5C5750',
    borde: '#D8D3CB',
  },
  oscuro: {
    card: '#1E293B',
    acento: '#2563EB',
    exito: '#10B981',
    advertencia: '#F59E0B',
    texto: '#F8FAFC',
    muted: '#94A3B8',
    borde: '#334155',
  },
}

export const TAMANO_CUERPO = 14
