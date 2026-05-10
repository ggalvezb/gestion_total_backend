from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.compra import AgregarParcialRequest, ParcialUpdate
from app.services import compra_service

router = APIRouter(prefix="/compras", tags=["Compras"])


@router.get("/cotizacion/{cotizacion_id}")
async def get_compra(
    cotizacion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Devuelve la compra completa con sus items y parciales."""
    return await compra_service.get_compra_con_items(db, cotizacion_id)


@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = await db.compra_items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    item["_id"] = str(item["_id"])
    item["compra_id"] = str(item["compra_id"])
    item["cotizacion_id"] = str(item["cotizacion_id"])
    item["completo"] = item["cantidad_comprada"] >= item["cantidad_total"]
    return item


@router.post("/items/{item_id}/parciales", status_code=201)
async def agregar_parcial(
    item_id: str,
    data: AgregarParcialRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Registra una compra parcial de un producto.
    Puede llamarse múltiples veces (distintos proveedores, distintos precios).
    """
    item = await compra_service.agregar_parcial(db, item_id, data.parcial)
    item["_id"] = str(item["_id"])
    item["compra_id"] = str(item["compra_id"])
    item["cotizacion_id"] = str(item["cotizacion_id"])
    item["completo"] = item["cantidad_comprada"] >= item["cantidad_total"]
    return item


@router.patch("/items/{item_id}/parciales/{parcial_idx}")
async def actualizar_parcial(
    item_id: str,
    parcial_idx: int,
    data: ParcialUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = await compra_service.actualizar_parcial(db, item_id, parcial_idx, data)
    item["_id"] = str(item["_id"])
    item["compra_id"] = str(item["compra_id"])
    item["cotizacion_id"] = str(item["cotizacion_id"])
    item["completo"] = item["cantidad_comprada"] >= item["cantidad_total"]
    return item


@router.delete("/items/{item_id}/parciales/{parcial_idx}", status_code=204)
async def eliminar_parcial(
    item_id: str,
    parcial_idx: int,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await compra_service.eliminar_parcial(db, item_id, parcial_idx)


@router.patch("/{compra_id}/notas")
async def actualizar_notas(
    compra_id: str,
    notas: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.compras.update_one(
        {"_id": ObjectId(compra_id)},
        {"$set": {"notas": notas}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return {"ok": True}
