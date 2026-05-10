from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from app.schemas.base import MongoBaseModel, PyObjectId


class EstadoCompra(str, Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    completada = "completada"


class ParcialCreate(BaseModel):
    """Una compra parcial de un ítem (a un proveedor específico)."""
    proveedor: str
    cantidad: int
    precio_unit: float      # precio unitario pagado (c/IVA)
    fecha: Optional[datetime] = Field(default_factory=datetime.utcnow)
    notas: str = ""


class ParcialOut(ParcialCreate):
    total: float            # calculado: cantidad * precio_unit


# ── Compra ────────────────────────────────────────────────

class CompraOut(MongoBaseModel):
    cotizacion_id: PyObjectId
    estado: EstadoCompra
    iniciada_en: datetime
    completada_en: Optional[datetime] = None
    total_pagado: float = 0
    notas: str = ""


# ── Compra Items ──────────────────────────────────────────

class CompraItemOut(MongoBaseModel):
    compra_id: PyObjectId
    cotizacion_id: PyObjectId
    producto_idx: int
    producto_desc: str
    cantidad_total: int
    cantidad_comprada: int       # sum(parciales[].cantidad)
    parciales: List[ParcialOut] = []
    completo: bool              # cantidad_comprada >= cantidad_total


class AgregarParcialRequest(BaseModel):
    parcial: ParcialCreate


class ParcialUpdate(BaseModel):
    proveedor: Optional[str] = None
    cantidad: Optional[int] = None
    precio_unit: Optional[float] = None
    notas: Optional[str] = None
