from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
from app.schemas.base import MongoBaseModel, PyObjectId


class TipoDocumento(str, Enum):
    # Compra (pueden ser múltiples)
    factura_compra = "factura_compra"
    boleta_compra = "boleta_compra"
    # Venta (generalmente 1 c/u)
    orden_de_compra = "orden_de_compra"
    guia_despacho = "guia_despacho"
    factura_venta = "factura_venta"
    factura_despacho = "factura_despacho"


TIPOS_COMPRA = {TipoDocumento.factura_compra, TipoDocumento.boleta_compra, TipoDocumento.factura_despacho}
TIPOS_VENTA = {
    TipoDocumento.orden_de_compra,
    TipoDocumento.guia_despacho,
    TipoDocumento.factura_venta,
}


class DocumentoOut(MongoBaseModel):
    cotizacion_id: PyObjectId
    tipo: TipoDocumento
    nombre_archivo: str
    storage_path: str
    url_descarga: str
    subido_por: PyObjectId
    subido_en: datetime
    monto: Optional[float] = None
    numero_doc: Optional[str] = None


class DocumentoMetadata(BaseModel):
    """Datos opcionales que se pueden enviar junto al archivo."""
    tipo: TipoDocumento
    monto: Optional[float] = None
    numero_doc: Optional[str] = None
