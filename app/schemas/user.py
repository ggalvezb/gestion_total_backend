from pydantic import BaseModel, EmailStr
from typing import Optional
from app.schemas.base import MongoBaseModel


class UserCreate(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str
    password: str
    rol: str = "ejecutivo"


class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = None


class UserOut(MongoBaseModel):
    nombre: str
    email: str
    telefono: str
    rol: str
    activo: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
