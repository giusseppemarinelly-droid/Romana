# Romana — Web de Supervisión

Frontend web de solo lectura para supervisores (React + TypeScript +
Vite + Tailwind). Ver `../docs/SPEC-web-supervision.md` para el spec y
`../tasks/plan.md` para el plan de implementación.

No reemplaza ni toca la app de escritorio: le habla al mismo backend
FastAPI (`../backend/`) por REST y WebSocket, y nunca escribe nada.

## ⚠ `dist/` está versionado en git

A propósito: así el servidor de planta sirve la web sin necesitar Node
(el backend la monta bajo `/supervision/`, ver `backend/main.py`). La
contracara es que **si cambiás algo en `src/`, tenés que correr
`npm run build` y commitear `dist/` en el mismo commit** — si no, el
servidor sigue sirviendo la versión anterior sin ningún aviso.

## Requisitos

Node 24 (fijado en `.nvmrc`). Con nvm: `nvm use` dentro de esta carpeta.

## Comandos

```bash
npm install
npm run dev      # servidor de desarrollo en :5173, con proxy de /api y /ws al backend
npm run build    # genera dist/ (esto es lo que sirve el backend en producción)
npm run test     # Vitest (una pasada); npm run test:watch para modo continuo
npm run lint
```

El proxy de desarrollo apunta a `http://127.0.0.1:8000` por defecto.
Para otro backend, exportar `ROMANA_API_URL` (misma variable que usa la
app de escritorio).

**Corriendo el dev server desde WSL** con el backend en Windows: WSL
(modo NAT) no ve el `127.0.0.1` de Windows, hay que apuntar a la IP del
host:

```bash
ROMANA_API_URL="http://$(ip route show default | awk '{print $3}'):8000" npm run dev
```
