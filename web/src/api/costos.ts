import type { Pesada } from '../types/pesada'
import { postJson } from './pesadas'

// Las dos decisiones de Centro de Costos: las únicas escrituras de datos
// del negocio que hace la web. El backend exige el permiso `centro_costos`
// en ambas y valida el estado (si otro usuario ya decidió, responde 400
// con el motivo en `detail`, que `postJson` convierte en un ErrorApi
// legible).

/**
 * Mínimo de caracteres del motivo de rechazo, igual que
 * `rechazar_pesada` en services/pesaje_service.py -- validarlo acá evita
 * un viaje al servidor solo para que responda "Debe ingresar un motivo".
 */
export const MOTIVO_MINIMO = 3

/** `comentario` opcional: por qué se aprueba (el backend guarda null si viene en blanco). */
export const aprobarPesada = (token: string, id: number, comentario = '') =>
  postJson<Pesada>(`/pesadas/${id}/aprobar`, token, { comentario: comentario.trim() })

export const rechazarPesada = (token: string, id: number, motivo: string) =>
  postJson<Pesada>(`/pesadas/${id}/rechazar`, token, { motivo: motivo.trim() })
