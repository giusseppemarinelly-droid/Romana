// Subconjunto de backend/schemas/pesada.py → PesadaOut: solo los campos
// que esta web usa. El backend manda bastantes más (pesos de guía,
// precintos, observaciones, etc.); agregarlos acá a medida que hagan
// falta, no "por las dudas".

export interface VehiculoDePesada {
  placa: string
  descripcion: string | null
}

export interface ProductoDePesada {
  codigo: string
  nombre: string
}

/** Los cuatro estados que muestra el tablero (hay más: rechazado, anulado). */
export type EstadoTablero = 'en_planta' | 'pendiente_aprobacion' | 'aprobado' | 'completado'

export interface Pesada {
  id: number
  numero_ticket: string
  estado: string
  tipo_pesaje: string

  fecha_entrada: string | null
  fecha_captura: string | null
  fecha_aprobacion: string | null
  fecha_salida: string | null

  peso_entrada: number | null
  peso_bruto: number | null
  peso_tara: number | null
  peso_neto: number | null

  codigo_viaje: string | null
  peso_guia: number | null
  bultos: number | null

  auto_aprobado: boolean
  es_manual: boolean

  empresa_transportista: string | null
  empresa_cliente_proveedor: string | null

  vehiculo: VehiculoDePesada | null
  producto: ProductoDePesada | null
}
