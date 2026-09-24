// Datos y dobles de prueba compartidos por los tests de pantallas. Cada
// archivo de test instala su propio backend falso con `instalarBackendFalso`
// y le pasa las rutas que necesita.
import { vi } from 'vitest'
import type { Sesion } from './types/auth'
import type { Pesada } from './types/pesada'

export class WebSocketFalso {
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  close() {}
}

export function sesionDe(nivel: number): Sesion {
  const nombres: Record<number, string> = {
    1: 'Administrador',
    2: 'Supervisor',
    3: 'Operador Romana',
    4: 'Centro de Costos',
  }
  return {
    token: 'token-de-prueba',
    usuario: {
      id: 1,
      username: `usuario${nivel}`,
      nombre_completo: `${nombres[nivel]} de Planta`,
      nivel,
      activo: true,
      last_login: null,
    },
    nivelNombre: nombres[nivel],
    expiraEn: Date.now() + 3_600_000,
  }
}

export function pesada(parcial: Partial<Pesada>): Pesada {
  return {
    id: 1,
    numero_ticket: 'TK-000001',
    estado: 'en_planta',
    tipo_pesaje: 'PRODUCTO_TERMINADO',
    fecha_entrada: new Date().toISOString(),
    fecha_captura: new Date().toISOString(),
    fecha_aprobacion: null,
    fecha_salida: null,
    peso_entrada: 10_000,
    peso_bruto: 20_000,
    peso_tara: 10_000,
    peso_neto: 10_000,
    codigo_viaje: '150',
    peso_guia: 12_000,
    bultos: 15,
    auto_aprobado: false,
    es_manual: false,
    empresa_transportista: null,
    empresa_cliente_proveedor: 'Farmatodo',
    vehiculo: { placa: 'ABC-123', descripcion: null },
    producto: { codigo: '001', nombre: 'Producto Terminado' },
    ...parcial,
  }
}

export const ESTADISTICAS = {
  dias: 14,
  generado: new Date().toISOString(),
  kpis: {
    en_planta: 1,
    pendientes_aprobacion: 1,
    completadas_hoy: 4,
    neto_hoy_kg: 40_000,
    minutos_promedio_hoy: 135,
    porcentaje_auto_aprobadas: 62.5,
  },
  serie_diaria: [
    { fecha: '2026-09-21', completadas: 2, minutos_promedio: 120 },
    { fecha: '2026-09-22', completadas: 4, minutos_promedio: 135 },
  ],
  distribucion_tipo: [
    { tipo: 'PRODUCTO_TERMINADO', cantidad: 5 },
    { tipo: 'GENERAL', cantidad: 1 },
  ],
}

export interface Llamada {
  url: string
  opciones?: RequestInit
}

/**
 * Reemplaza fetch y WebSocket por dobles. `porRuta` se recorre en orden:
 * gana la primera clave contenida en la URL, así que las más específicas
 * van primero. Un valor función recibe la llamada y devuelve
 * { status, cuerpo } (para simular errores o respuestas a un POST).
 * Devuelve la lista de llamadas hechas, para verificar métodos y cuerpos.
 */
export function instalarBackendFalso(
  porRuta: Record<string, unknown | ((l: Llamada) => { status: number; cuerpo: unknown })>,
): Llamada[] {
  const llamadas: Llamada[] = []
  vi.stubGlobal('WebSocket', WebSocketFalso)
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, opciones?: RequestInit) => {
      const llamada = { url, opciones }
      llamadas.push(llamada)
      const clave = Object.keys(porRuta).find((k) => url.includes(k))
      const valor = clave ? porRuta[clave] : []
      const { status, cuerpo } =
        typeof valor === 'function'
          ? (valor as (l: Llamada) => { status: number; cuerpo: unknown })(llamada)
          : { status: 200, cuerpo: valor }
      return Promise.resolve(new Response(JSON.stringify(cuerpo), { status }))
    }),
  )
  return llamadas
}
