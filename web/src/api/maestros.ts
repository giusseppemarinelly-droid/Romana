import type { Catalogos, ClaveCatalogo } from '../types/maestros'
import { getJson } from './pesadas'

// Rutas de backend/routers/maestros.py (crear_router_maestro), todas con
// permiso `maestros_ver`. Solo se usan los GET: la web no da de alta ni
// edita catálogos, eso sigue en la app de escritorio.
const RUTAS: Record<ClaveCatalogo, string> = {
  vehiculos: '/vehiculos',
  conductores: '/conductores',
  proveedores: '/proveedores',
  transportistas: '/empresas_transportistas',
}

// Mismo orden que usa el backend (`orden_por` de cada router).
const ORDEN: { [C in ClaveCatalogo]: (fila: Catalogos[C][number]) => string } = {
  vehiculos: (v) => v.placa,
  conductores: (c) => c.nombre,
  proveedores: (p) => p.nombre,
  transportistas: (t) => t.nombre,
}

/**
 * Catálogo completo, activos e inactivos.
 *
 * El listado del backend filtra `activo=true` por defecto y no hay forma
 * de pedir "todos" por query string (un `activo=` vacío no llega como
 * None), así que se piden las dos mitades en paralelo y se juntan. Sin
 * esto la columna Estado diría "Activo" en todas las filas y un vehículo
 * dado de baja simplemente no aparecería.
 *
 * No se usa `search` del backend: el catálogo es chico (decenas o pocos
 * cientos de filas) y filtrar en el cliente responde al instante sin
 * pedir nada por cada tecla.
 */
export async function obtenerCatalogo<C extends ClaveCatalogo>(
  clave: C,
  token: string,
): Promise<Catalogos[C]> {
  const ruta = RUTAS[clave]
  const [activos, inactivos] = await Promise.all([
    getJson<Catalogos[C]>(`${ruta}?activo=true`, token),
    getJson<Catalogos[C]>(`${ruta}?activo=false`, token),
  ])
  const orden = ORDEN[clave] as (fila: Catalogos[C][number]) => string
  return [...activos, ...inactivos].sort((a, b) =>
    orden(a).localeCompare(orden(b), 'es', { sensitivity: 'base' }),
  ) as Catalogos[C]
}
