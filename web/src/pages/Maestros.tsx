import { useId, useState, type ReactNode } from 'react'
import { Marco, type PropsPagina } from '../components/Marco'
import { Pestanas, type Pestana } from '../components/Pestanas'
import { Punto } from '../components/Punto'
import { useCatalogo } from '../hooks/useCatalogo'
import type { Catalogos, ClaveCatalogo, Conductor, Empresa, Vehiculo } from '../types/maestros'
import { coincide } from '../utils/busqueda'
import { idsPestana } from '../utils/pestanas'
import { formatearKg } from '../utils/pesadas'

// Pantalla de consulta de los catálogos. Solo lectura a propósito: las
// altas, cambios y bajas siguen en Maestros de la app de escritorio (la
// web no escribe datos del negocio, ver docs/SPEC-web-supervision.md).

const PESTANAS: Pestana<ClaveCatalogo>[] = [
  { clave: 'vehiculos', etiqueta: 'Vehículos' },
  { clave: 'conductores', etiqueta: 'Choferes' },
  { clave: 'proveedores', etiqueta: 'Proveedores' },
  { clave: 'transportistas', etiqueta: 'Transportistas' },
]

interface Columna<T> {
  titulo: string
  /** Texto de la celda; también es lo que recorre el buscador. */
  valor: (fila: T) => string
  estilo?: 'principal' | 'tenue' | 'numero'
}

// Valores que guarda la app de escritorio (gui/maestros/*_view.py), en
// minúscula y sin tildes; acá solo se escriben bien para leerlos.
const TIPOS_VEHICULO: Record<string, string> = {
  camion: 'Camión',
  tractocamion: 'Tractocamión',
  volqueta: 'Volqueta',
  cisterna: 'Cisterna',
  otro: 'Otro',
}
const TIPOS_DOCUMENTO: Record<string, string> = {
  cedula: 'Cédula',
  licencia: 'Licencia',
  pasaporte: 'Pasaporte',
}

/** Valor legible de un catálogo cerrado; si llega uno nuevo se muestra tal cual. */
const legible = (tabla: Record<string, string>, valor: string | null) =>
  valor ? (tabla[valor] ?? valor) : '—'

const COLUMNAS_EMPRESA: Columna<Empresa>[] = [
  { titulo: 'Código', valor: (e) => e.codigo, estilo: 'principal' },
  { titulo: 'Nombre', valor: (e) => e.nombre },
  { titulo: 'RIF', valor: (e) => e.rif || '—' },
  { titulo: 'Teléfono', valor: (e) => e.telefono || '—', estilo: 'tenue' },
  { titulo: 'Correo', valor: (e) => e.email || '—', estilo: 'tenue' },
]

// Columnas sacadas de los campos reales de backend/schemas/maestros.py.
// Quedan afuera a propósito: la dirección de las empresas (texto largo
// que desarma la tabla) y el proveedor asociado al vehículo (el listado
// trae solo `proveedor_id`; resolver el nombre obligaría a pedir también
// el catálogo de proveedores al abrir Vehículos).
const COLUMNAS: { [C in ClaveCatalogo]: Columna<Catalogos[C][number]>[] } = {
  vehiculos: [
    { titulo: 'Placa', valor: (v: Vehiculo) => v.placa, estilo: 'principal' },
    { titulo: 'Descripción', valor: (v: Vehiculo) => v.descripcion || '—' },
    { titulo: 'Tipo', valor: (v: Vehiculo) => legible(TIPOS_VEHICULO, v.tipo), estilo: 'tenue' },
    {
      titulo: 'Tara registrada (kg)',
      valor: (v: Vehiculo) => formatearKg(v.tara_registrada),
      estilo: 'numero',
    },
  ],
  conductores: [
    { titulo: 'Nombre', valor: (c: Conductor) => c.nombre, estilo: 'principal' },
    { titulo: 'Documento', valor: (c: Conductor) => c.documento },
    {
      titulo: 'Tipo de documento',
      valor: (c: Conductor) => legible(TIPOS_DOCUMENTO, c.tipo_documento),
      estilo: 'tenue',
    },
    { titulo: 'Teléfono', valor: (c: Conductor) => c.telefono || '—', estilo: 'tenue' },
  ],
  proveedores: COLUMNAS_EMPRESA,
  transportistas: COLUMNAS_EMPRESA,
}

const TEXTOS: Record<ClaveCatalogo, { plural: string; ayuda: string }> = {
  vehiculos: { plural: 'vehículos', ayuda: 'Buscar por placa, descripción o tipo' },
  conductores: { plural: 'choferes', ayuda: 'Buscar por nombre, documento o teléfono' },
  proveedores: { plural: 'proveedores', ayuda: 'Buscar por código, nombre, RIF o correo' },
  transportistas: { plural: 'transportistas', ayuda: 'Buscar por código, nombre, RIF o correo' },
}

export function Maestros(props: PropsPagina) {
  const [actual, setActual] = useState<ClaveCatalogo>('vehiculos')
  // Una búsqueda por pestaña: ir a mirar otro catálogo y volver no borra
  // lo que se había escrito.
  const [busquedas, setBusquedas] = useState<Partial<Record<ClaveCatalogo, string>>>({})
  const base = useId()

  const { datos, error, actualizado, conectado, recargar } = useCatalogo(
    props.sesion.token,
    actual,
    props.onCerrarSesion,
  )

  return (
    <Marco
      {...props}
      titulo="Maestros"
      descripcion="Catálogos de solo lectura. Las altas y los cambios se hacen desde la app de escritorio."
      conectado={conectado}
      actualizado={actualizado}
      error={error}
      onReintentar={recargar}
    >
      <Pestanas
        base={base}
        etiqueta="Catálogos"
        pestanas={PESTANAS}
        actual={actual}
        onCambiar={setActual}
      />

      {/* Un panel por pestaña (así cada aria-controls apunta a algo que
          existe), pero solo el visible tiene contenido. */}
      {PESTANAS.map(({ clave }) => {
        const ids = idsPestana(base, clave)
        return (
          <div
            key={clave}
            role="tabpanel"
            id={ids.panel}
            aria-labelledby={ids.pestana}
            hidden={clave !== actual}
            className="flex flex-col gap-2"
          >
            {clave === actual &&
              (datos ? (
                <PanelCatalogo
                  clave={actual}
                  filas={datos}
                  busqueda={busquedas[actual] ?? ''}
                  onBuscar={(texto) => setBusquedas((b) => ({ ...b, [actual]: texto }))}
                />
              ) : (
                // Con error, el aviso con "Reintentar" ya lo muestra Marco.
                !error && <p className="text-muted">Cargando…</p>
              ))}
          </div>
        )
      })}
    </Marco>
  )
}

/** Une el catálogo con sus columnas conservando el tipo de fila de cada uno. */
function PanelCatalogo<C extends ClaveCatalogo>({
  clave,
  filas,
  busqueda,
  onBuscar,
}: {
  clave: C
  filas: Catalogos[C]
  busqueda: string
  onBuscar: (texto: string) => void
}) {
  return (
    <TablaCatalogo<Catalogos[C][number]>
      columnas={COLUMNAS[clave]}
      filas={filas}
      busqueda={busqueda}
      onBuscar={onBuscar}
      {...TEXTOS[clave]}
    />
  )
}

const TH = 'px-2 font-semibold text-muted'
const TD = 'px-2'
const CLASE_CELDA: Record<NonNullable<Columna<unknown>['estilo']>, string> = {
  principal: `${TD} font-semibold`,
  tenue: `${TD} text-muted`,
  numero: `${TD} text-right tabular-nums`,
}

function TablaCatalogo<T extends { id: number; activo: boolean }>({
  columnas,
  filas,
  busqueda,
  onBuscar,
  plural,
  ayuda,
}: {
  columnas: Columna<T>[]
  filas: T[]
  busqueda: string
  onBuscar: (texto: string) => void
  plural: string
  ayuda: string
}) {
  // Se filtra sobre el mismo texto que se ve en las celdas: si algo está
  // en pantalla, se puede buscar (incluido "Camión" o "Cédula").
  const visibles = filas.filter((f) =>
    coincide(
      columnas.map((c) => c.valor(f)),
      busqueda,
    ),
  )

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={busqueda}
          onChange={(e) => onBuscar(e.target.value)}
          placeholder={ayuda}
          aria-label={ayuda}
          className="h-5 w-full max-w-60 rounded-control border border-borde bg-fondo px-2 text-texto outline-none focus:border-acento"
        />
        <p className="text-muted tabular-nums" aria-live="polite">
          {visibles.length} de {filas.length} {plural}
        </p>
      </div>

      {filas.length === 0 ? (
        <Vacio>No hay {plural} registrados.</Vacio>
      ) : visibles.length === 0 ? (
        <Vacio>Ningún resultado para «{busqueda.trim()}».</Vacio>
      ) : (
        <div className="overflow-x-auto rounded-card border border-borde bg-card">
          <table className="w-full min-w-88 border-collapse">
            <thead>
              <tr className="h-6 border-b border-borde">
                {columnas.map((c) => (
                  <th
                    key={c.titulo}
                    className={`${TH} ${c.estilo === 'numero' ? 'text-right' : 'text-left'}`}
                  >
                    {c.titulo}
                  </th>
                ))}
                <th className={`${TH} text-left`}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((fila) => (
                <tr
                  key={fila.id}
                  className="h-6 border-b border-borde transition-colors last:border-0 hover:bg-borde"
                >
                  {columnas.map((c) => (
                    <td key={c.titulo} className={c.estilo ? CLASE_CELDA[c.estilo] : TD}>
                      {c.valor(fila)}
                    </td>
                  ))}
                  <td className={TD}>
                    <EstadoActivo activo={fila.activo} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function EstadoActivo({ activo }: { activo: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <Punto color={activo ? 'bg-exito' : 'bg-muted'} />
      {activo ? 'Activo' : 'Inactivo'}
    </span>
  )
}

function Vacio({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-card border border-borde bg-card p-4 text-center text-muted">{children}</p>
  )
}
