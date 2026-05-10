from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/costos-fijos", tags=["Costos Fijos"])


class CostoFijoCreate(BaseModel):
    nombre: str
    valor_mensual: float
    orden: int = 0


class CostoFijoUpdate(BaseModel):
    nombre: Optional[str] = None
    valor_mensual: Optional[float] = None
    activo: Optional[bool] = None
    orden: Optional[int] = None


@router.get("")
async def listar(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    docs = await db.costos_fijos.find().sort("orden", 1).to_list(None)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@router.post("", status_code=201)
async def crear(
    data: CostoFijoCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = {**data.model_dump(), "activo": True}
    result = await db.costos_fijos.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.patch("/{costo_id}")
async def actualizar(
    costo_id: str,
    data: CostoFijoUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    result = await db.costos_fijos.update_one(
        {"_id": ObjectId(costo_id)}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Costo fijo no encontrado")
    doc = await db.costos_fijos.find_one({"_id": ObjectId(costo_id)})
    doc["_id"] = str(doc["_id"])
    return doc


@router.delete("/{costo_id}", status_code=204)
async def eliminar(
    costo_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.costos_fijos.delete_one({"_id": ObjectId(costo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Costo fijo no encontrado")
