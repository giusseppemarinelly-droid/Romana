# ============================================================
# backend/routers/reportes.py
# ============================================================
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from backend.deps import requiere_permiso
from backend.routers.pesadas import _obtener_pesada
from services import pesaje_service, reporte_service

router = APIRouter(prefix="/reportes", tags=["reportes"])

PDF_MEDIA_TYPE = "application/pdf"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _adjunto(nombre: str) -> dict:
    return {"Content-Disposition": f'attachment; filename="{nombre}"'}


@router.get("/ticket/{pesada_id}.pdf", dependencies=[Depends(requiere_permiso("reportes_ver"))])
async def ticket_pdf(pesada_id: int):
    pesada = await _obtener_pesada(pesada_id)
    contenido = await run_in_threadpool(reporte_service.generar_ticket_pdf, pesada)
    return Response(
        content=contenido, media_type=PDF_MEDIA_TYPE,
        headers=_adjunto(f"TICKET_{pesada.numero_ticket}.pdf"),
    )


@router.get("/kardex.pdf", dependencies=[Depends(requiere_permiso("reportes_exportar"))])
async def kardex_pdf(
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    producto_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    vehiculo_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit: int = 500,
):
    pesadas = await run_in_threadpool(
        pesaje_service.get_kardex,
        fecha_inicio, fecha_fin, producto_id, proveedor_id, vehiculo_id, estado, limit,
    )
    contenido = await run_in_threadpool(reporte_service.generar_kardex_pdf, pesadas)
    nombre = f"KARDEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(content=contenido, media_type=PDF_MEDIA_TYPE, headers=_adjunto(nombre))


@router.get("/kardex.xlsx", dependencies=[Depends(requiere_permiso("reportes_exportar"))])
async def kardex_excel(
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    producto_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    vehiculo_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit: int = 500,
):
    pesadas = await run_in_threadpool(
        pesaje_service.get_kardex,
        fecha_inicio, fecha_fin, producto_id, proveedor_id, vehiculo_id, estado, limit,
    )
    contenido = await run_in_threadpool(reporte_service.generar_kardex_excel, pesadas)
    nombre = f"KARDEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(content=contenido, media_type=XLSX_MEDIA_TYPE, headers=_adjunto(nombre))
