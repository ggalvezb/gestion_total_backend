from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


class ProveedorCreate(BaseModel):
    nombre: str
    rut: Optional[str] = None
    rubro: Optional[str] = None
    contacto: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None


class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = None
    rut: Optional[str] = None
    rubro: Optional[str] = None
    contacto: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("")
async def listar(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    docs = await db.proveedores.find().sort("nombre", 1).to_list(None)
    return [_serialize(d) for d in docs]


@router.get("/{proveedor_id}")
async def obtener(
    proveedor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = await db.proveedores.find_one({"_id": ObjectId(proveedor_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return _serialize(doc)


@router.post("", status_code=201)
async def crear(
    data: ProveedorCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = {**data.model_dump(), "activo": True}
    result = await db.proveedores.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.patch("/{proveedor_id}")
async def actualizar(
    proveedor_id: str,
    data: ProveedorUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    result = await db.proveedores.update_one(
        {"_id": ObjectId(proveedor_id)}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    doc = await db.proveedores.find_one({"_id": ObjectId(proveedor_id)})
    return _serialize(doc)


@router.delete("/{proveedor_id}", status_code=204)
async def eliminar(
    proveedor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.proveedores.delete_one({"_id": ObjectId(proveedor_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
