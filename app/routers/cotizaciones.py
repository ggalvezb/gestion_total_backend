from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.cotizacion import (
    CotizacionCreate, CotizacionUpdate, CotizacionOut,
    CotizacionListItem, CambiarEstadoRequest, EstadoCotizacion
)
from app.services import cotizacion_service
from app.services.storage_service import eliminar_archivo

router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


def _serialize(doc: dict) -> dict:
    """Convierte ObjectIds a string para la respuesta."""
    doc["_id"] = str(doc["_id"])
    doc["ejecutivo_id"] = str(doc["ejecutivo_id"])
    return doc


@router.get("", response_model=List[dict])
async def listar(
    estado: Optional[EstadoCotizacion] = None,
    ejecutivo_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lista cotizaciones con filtros opcionales."""
    filtro = {}
    if estado:
        filtro["estado"] = estado
    if ejecutivo_id:
        filtro["ejecutivo_id"] = ObjectId(ejecutivo_id)

    cursor = db.cotizaciones.find(filtro).sort("creado_en", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    return [_serialize(d) for d in docs]


@router.post("", status_code=201)
async def crear(
    data: CotizacionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await cotizacion_service.crear_cotizacion(
        db, data, ejecutivo_id=current_user["_id"]
    )
    return _serialize(doc)


@router.get("/{cot_id}")
async def obtener(
    cot_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.cotizaciones.find_one({"_id": ObjectId(cot_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return _serialize(doc)


@router.patch("/{cot_id}")
async def actualizar(
    cot_id: str,
    data: CotizacionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await cotizacion_service.actualizar_cotizacion(
        db, cot_id, data, ejecutivo_id=current_user["_id"]
    )
    return _serialize(doc)


@router.patch("/{cot_id}/estado")
async def cambiar_estado(
    cot_id: str,
    data: CambiarEstadoRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Cambia el estado de una cotización respetando las transiciones válidas.
    Al pasar a 'aprobada' se crea automáticamente el proceso de compra.
    """
    doc = await cotizacion_service.cambiar_estado(
        db, cot_id, data.estado, ejecutivo_id=current_user["_id"]
    )
    return _serialize(doc)


@router.delete("/{cot_id}", status_code=204)
async def eliminar(
    cot_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cot = await db.cotizaciones.find_one({"_id": ObjectId(cot_id)})
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    oid = ObjectId(cot_id)

    # Eliminar archivos del storage y sus registros
    documentos = await db.documentos.find({"cotizacion_id": oid}).to_list(None)
    for doc in documentos:
        await eliminar_archivo(doc["storage_path"])
    await db.documentos.delete_many({"cotizacion_id": oid})

    # Eliminar compra e items asociados
    compra = await db.compras.find_one({"cotizacion_id": oid})
    if compra:
        await db.compra_items.delete_many({"compra_id": compra["_id"]})
        await db.compras.delete_one({"_id": compra["_id"]})

    await db.cotizaciones.delete_one({"_id": oid})
