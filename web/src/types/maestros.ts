// Espejo de backend/schemas/maestros.py → *Out. Acá van todos los
// campos que manda el backend (son pocos), aunque la tabla no muestre
// alguno (ej. la dirección): así el tipo no miente sobre lo que llega.

export interface Vehiculo {
  id: number
  placa: string
  descripcion: string | null
  tara_registrada: number | null
  tipo: string | null
  /** Solo el id: el backend no lo resuelve a nombre en este listado. */
  proveedor_id: number | null
  activo: boolean
}

export interface Conductor {
  id: number
  nombre: string
  documento: string
  tipo_documento: string | null
  telefono: string | null
  activo: boolean
}

/** Mismo formato para proveedores (clientes/proveedores) y transportistas. */
export interface Empresa {
  id: number
  codigo: string
  nombre: string
  rif: string | null
  direccion: string | null
  telefono: string | null
  email: string | null
  activo: boolean
}

export type Proveedor = Empresa
export type EmpresaTransportista = Empresa

/** Lo que trae cada pestaña de la pantalla Maestros. */
export interface Catalogos {
  vehiculos: Vehiculo[]
  conductores: Conductor[]
  proveedores: Proveedor[]
  transportistas: EmpresaTransportista[]
}

export type ClaveCatalogo = keyof Catalogos
