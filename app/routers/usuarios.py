from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    doc.pop("password_hash", None)
    return doc


@router.get("")
async def listar(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    users = await db.users.find().sort("nombre", 1).to_list(None)
    return [_serialize(u) for u in users]


@router.post("", status_code=201)
async def crear(
    data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    doc = {
        "nombre": data.nombre,
        "email": data.email,
        "telefono": data.telefono,
        "rol": data.rol,
        "activo": True,
        "password_hash": hash_password(data.password),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


@router.patch("/{user_id}")
async def actualizar(
    user_id: str,
    data: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updates = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "password"}

    if data.email and data.email != user["email"]:
        if await db.users.find_one({"email": data.email}):
            raise HTTPException(status_code=400, detail="El email ya está registrado")

    if data.password:
        updates["password_hash"] = hash_password(data.password)

    if updates:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})

    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    return _serialize(doc)


@router.delete("/{user_id}", status_code=204)
async def eliminar(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await db.users.delete_one({"_id": ObjectId(user_id)})
