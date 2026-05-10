from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, hash_password, get_current_user
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not user.get("activo", True):
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    token = create_access_token({"sub": str(user["_id"])})
    user_out = UserOut(
        _id=str(user["_id"]),
        nombre=user["nombre"],
        email=user["email"],
        telefono=user["telefono"],
        rol=user["rol"],
        activo=user["activo"],
    )
    return TokenResponse(access_token=token, user=user_out)


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return UserOut(
        _id=str(current_user["_id"]),
        nombre=current_user["nombre"],
        email=current_user["email"],
        telefono=current_user["telefono"],
        rol=current_user["rol"],
        activo=current_user["activo"],
    )


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Endpoint para crear usuarios (proteger en producción)."""
    existing = await db.users.find_one({"email": data.email})
    if existing:
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
    return UserOut(_id=str(result.inserted_id), **{k: v for k, v in doc.items() if k != "password_hash"})
