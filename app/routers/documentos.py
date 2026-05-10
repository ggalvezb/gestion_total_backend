from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.schemas.documento import TipoDocumento, TIPOS_COMPRA, TIPOS_VENTA
from app.services.storage_service import guardar_archivo, eliminar_archivo

settings = get_settings()
router = APIRouter(prefix="/documentos", tags=["Documentos"])

TIPOS_PERMITIDOS = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 20


@router.get("/cotizacion/{cotizacion_id}")
async def listar_documentos(
    cotizacion_id: str,
    tipo: Optional[TipoDocumento] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lista todos los documentos de una cotización, opcionalmente filtrado por tipo."""
    filtro = {"cotizacion_id": ObjectId(cotizacion_id)}
    if tipo:
        filtro["tipo"] = tipo

    docs = await db.documentos.find(filtro).sort("subido_en", -1).to_list(None)
    for d in docs:
        d["_id"] = str(d["_id"])
        d["cotizacion_id"] = str(d["cotizacion_id"])
        d["subido_por"] = str(d["subido_por"])
    return docs


@router.post("/cotizacion/{cotizacion_id}", status_code=201)
async def subir_documento(
    cotizacion_id: str,
    tipo: TipoDocumento = Form(...),
    file: UploadFile = File(...),
    monto: Optional[float] = Form(None),
    numero_doc: Optional[str] = Form(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Sube un documento PDF/imagen asociado a una cotización.
    - tipo: factura_compra | boleta_compra | orden_de_compra | guia_despacho | factura_venta | factura_despacho
    - Para documentos de venta únicos (orden_de_compra, guia_despacho, etc.) se reemplaza si ya existe.
    """
    # Validar que la cotización existe y está en estado correcto
    cot = await db.cotizaciones.find_one({"_id": ObjectId(cotizacion_id)})
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    if cot["estado"] not in ("aprobada", "en_compra", "comprada", "despachado"):
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden adjuntar documentos a cotizaciones aprobadas o en compra"
        )

    # Validar tipo de archivo
    if file.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Usa: PDF, JPG, PNG"
        )

    # Documentos de venta únicos: eliminar el anterior si existe
    tipo_enum = TipoDocumento(tipo)
    if tipo_enum in TIPOS_VENTA:
        existing = await db.documentos.find_one({
            "cotizacion_id": ObjectId(cotizacion_id),
            "tipo": tipo
        })
        if existing:
            await eliminar_archivo(existing["storage_path"])
            await db.documentos.delete_one({"_id": existing["_id"]})

    # Guardar archivo
    storage_path, url_descarga = await guardar_archivo(file, cotizacion_id, tipo)

    doc = {
        "cotizacion_id": ObjectId(cotizacion_id),
        "tipo": tipo,
        "nombre_archivo": file.filename,
        "storage_path": storage_path,
        "url_descarga": url_descarga,
        "subido_por": current_user["_id"],
        "subido_en": datetime.utcnow(),
        "monto": monto,
        "numero_doc": numero_doc,
    }
    result = await db.documentos.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc["cotizacion_id"] = cotizacion_id
    doc["subido_por"] = str(current_user["_id"])
    return doc


@router.delete("/{doc_id}", status_code=204)
async def eliminar_documento(
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.documentos.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    await eliminar_archivo(doc["storage_path"])
    await db.documentos.delete_one({"_id": ObjectId(doc_id)})


# Endpoint para servir archivos locales
@router.get("/files/{path:path}")
async def servir_archivo(path: str, current_user=Depends(get_current_user)):
    """Sirve archivos guardados localmente."""
    full_path = Path(settings.storage_local_path) / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(full_path)
