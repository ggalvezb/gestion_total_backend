from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from app.schemas.base import MongoBaseModel, PyObjectId


class EstadoCotizacion(str, Enum):
    borrador = "borrador"
    enviada = "enviada"
    aprobada = "aprobada"
    en_compra = "en_compra"
    comprada = "comprada"
    despachado = "despachado"
    rechazada = "rechazada"
    expirada = "expirada"
    desierta = "desierta"


# ── Sub-modelos embebidos ──────────────────────────────────

class ClienteEmbed(BaseModel):
    nombre: str
    rut: str
    direccion: str
    ciudad: str


class ParametrosEmbed(BaseModel):
    pct_costo_fijo: float = 5.0
    pct_utilidad: float = 11.0
    costo_transporte: float = 0.0


class FichaEmbed(BaseModel):
    descripcion: str = ""
    foto_url: str = ""


class ProductoEmbed(BaseModel):
    idx: int
    desc: str
    cantidad: int
    precio_compra: float          # precio c/IVA tal como lo ingresa el usuario
    link_fuente: str = ""
    ficha: FichaEmbed = Field(default_factory=FichaEmbed)


class CalculosEmbed(BaseModel):
    valor_compra: float = 0
    iva_debito: float = 0
    costo_fijo_monto: float = 0
    costo_transporte: float = 0
    precio_costo_final: float = 0
    utilidad_monto: float = 0
    neto_venta: float = 0
    iva_credito: float = 0
    precio_venta_total: float = 0


# ── Requests / Responses ──────────────────────────────────

class CotizacionCreate(BaseModel):
    numero: Optional[str] = None        # si no se pasa, se autogenera
    cliente: ClienteEmbed
    parametros: ParametrosEmbed = Field(default_factory=ParametrosEmbed)
    productos: List[ProductoEmbed] = []
    validez_dias: int = 30
    despacho_dias: int = 3


class CotizacionUpdate(BaseModel):
    cliente: Optional[ClienteEmbed] = None
    parametros: Optional[ParametrosEmbed] = None
    productos: Optional[List[ProductoEmbed]] = None
    validez_dias: Optional[int] = None
    despacho_dias: Optional[int] = None
    estado: Optional[EstadoCotizacion] = None


class CotizacionOut(MongoBaseModel):
    numero: str
    estado: EstadoCotizacion
    ejecutivo_id: PyObjectId
    creado_en: datetime
    validez_dias: int
    despacho_dias: int
    cliente: ClienteEmbed
    parametros: ParametrosEmbed
    productos: List[ProductoEmbed]
    calculos: CalculosEmbed


class CotizacionListItem(MongoBaseModel):
    """Versión reducida para la tabla del Home."""
    numero: str
    estado: EstadoCotizacion
    ejecutivo_id: PyObjectId
    creado_en: datetime
    cliente: ClienteEmbed
    calculos: CalculosEmbed


class CambiarEstadoRequest(BaseModel):
    estado: EstadoCotizacion
