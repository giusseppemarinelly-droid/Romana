// Subconjunto de backend/schemas/pesada.py → PesadaOut: solo los campos
// que esta web usa. El backend manda bastantes más (pesos de guía,
// precintos, observaciones, etc.); agregarlos acá a medida que hagan
// falta, no "por las dudas".

export interface VehiculoDePesada {
  placa: string
  descripcion: string | null
  tipo?: string | null
}

export interface ProductoDePesada {
  codigo: string
  nombre: string
}

/** backend/schemas/maestros.py → ConductorOut (lo que usa el detalle). */
export interface ConductorDePesada {
  nombre: string
  documento: string
  tipo_documento?: string | null
}

/** ProveedorOut y EmpresaTransportistaOut tienen la misma forma. */
export interface EmpresaDePesada {
  codigo: string
  nombre: string
  rif?: string | null
}

export interface DestinoDePesada {
  codigo: string
  nombre: string
}

/** backend/schemas/auth.py → UsuarioOut, reducido a lo que se muestra. */
export interface UsuarioDePesada {
  id: number
  username: string
  nombre_completo: string
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

  // --- Detalle completo (GET /pesadas/{id}, también el kardex) ---
  // Opcionales a propósito: los listados del tablero y los datos de
  // prueba no siempre los traen, y el detalle tiene que tolerar su
  // ausencia igual que un null (pesadas viejas, anteriores al campo).
  peso_final?: number | null
  anulada?: boolean
  cedula_conductor_libre?: string | null
  procedencia?: string | null
  orden_compra?: string | null
  cantidad?: number | null
  precintos?: string | null
  observaciones?: string | null
  motivo_rechazo?: string | null
  /** Por qué aprobó Costos (opcional). */
  comentario_aprobacion?: string | null
  motivo_anulacion?: string | null
  fecha_anulacion?: string | null

  conductor?: ConductorDePesada | null
  proveedor?: EmpresaDePesada | null
  transportista?: EmpresaDePesada | null
  destino?: DestinoDePesada | null

  // Quién hizo cada etapa: con esto y las fechas se arma el recorrido
  // (el backend no guarda un historial de auditoría aparte).
  usuario_entrada?: UsuarioDePesada | null
  usuario_salida?: UsuarioDePesada | null
  aprobado_por?: UsuarioDePesada | null
  usuario_completado?: UsuarioDePesada | null
  anulado_por?: UsuarioDePesada | null
}
