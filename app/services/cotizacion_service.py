from datetime import datetime
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from app.schemas.cotizacion import (
    CotizacionCreate, CotizacionUpdate, EstadoCotizacion, CalculosEmbed
)


IVA = 0.19
IVA_FACTOR = 1.19

# Transiciones de estado permitidas
TRANSICIONES_VALIDAS = {
    EstadoCotizacion.borrador:   {EstadoCotizacion.enviada, EstadoCotizacion.rechazada},
    EstadoCotizacion.enviada:    {EstadoCotizacion.aprobada, EstadoCotizacion.rechazada, EstadoCotizacion.expirada},
    EstadoCotizacion.aprobada:   {EstadoCotizacion.en_compra, EstadoCotizacion.rechazada},
    EstadoCotizacion.en_compra:  {EstadoCotizacion.comprada},
    EstadoCotizacion.comprada:   {EstadoCotizacion.despachado},
    EstadoCotizacion.despachado: set(),
    EstadoCotizacion.rechazada:  {EstadoCotizacion.borrador},
    EstadoCotizacion.expirada:   {EstadoCotizacion.borrador},
}


def calcular(productos: list, parametros: dict, costos_fijos_total: float = 0) -> dict:
    """Ejecuta el mismo cálculo que el HTML original."""
    pct_fijo = parametros.get("pct_costo_fijo", 5) / 100
    pct_util = parametros.get("pct_utilidad", 11) / 100
    transporte = parametros.get("costo_transporte", 0)

    valor_compra = sum(p["cantidad"] * p["precio_compra"] for p in productos)
    iva_debito = valor_compra - (valor_compra / IVA_FACTOR)
    costo_fijo_monto = costos_fijos_total * pct_fijo
    precio_costo_final = (valor_compra / IVA_FACTOR) + costo_fijo_monto + transporte
    neto_venta = precio_costo_final * (1 + pct_util)
    iva_credito = neto_venta * IVA
    precio_venta_total = neto_venta + iva_credito
    utilidad_monto = neto_venta - precio_costo_final

    return {
        "valor_compra": round(valor_compra, 0),
        "iva_debito": round(iva_debito, 0),
        "costo_fijo_monto": round(costo_fijo_monto, 0),
        "costo_transporte": round(transporte, 0),
        "precio_costo_final": round(precio_costo_final, 0),
        "utilidad_monto": round(utilidad_monto, 0),
        "neto_venta": round(neto_venta, 0),
        "iva_credito": round(iva_credito, 0),
        "precio_venta_total": round(precio_venta_total, 0),
    }


async def generar_numero(db: AsyncIOMotorDatabase) -> str:
    """Genera número correlativo tipo COT-2025-001."""
    year = datetime.utcnow().year
    prefix = f"COT-{year}-"
    last = await db.cotizaciones.find_one(
        {"numero": {"$regex": f"^{prefix}"}},
        sort=[("numero", -1)]
    )
    if last:
        try:
            last_num = int(last["numero"].split("-")[-1])
        except ValueError:
            last_num = 0
    else:
        last_num = 0
    return f"{prefix}{str(last_num + 1).zfill(3)}"


async def crear_cotizacion(
    db: AsyncIOMotorDatabase,
    data: CotizacionCreate,
    ejecutivo_id: ObjectId,
) -> dict:
    numero = data.numero or await generar_numero(db)

    # Obtener total de costos fijos para el cálculo
    costos = await db.costos_fijos.find({"activo": True}).to_list(None)
    costos_total = sum(c["valor_mensual"] for c in costos)

    productos_list = [p.model_dump() for p in data.productos]
    calculos = calcular(productos_list, data.parametros.model_dump(), costos_total)

    doc = {
        "numero": numero,
        "estado": EstadoCotizacion.borrador,
        "ejecutivo_id": ejecutivo_id,
        "creado_en": datetime.utcnow(),
        "validez_dias": data.validez_dias,
        "despacho_dias": data.despacho_dias,
        "cliente": data.cliente.model_dump(),
        "parametros": data.parametros.model_dump(),
        "productos": productos_list,
        "calculos": calculos,
    }

    result = await db.cotizaciones.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def actualizar_cotizacion(
    db: AsyncIOMotorDatabase,
    cot_id: str,
    data: CotizacionUpdate,
    ejecutivo_id: ObjectId,
) -> dict:
    cot = await db.cotizaciones.find_one({"_id": ObjectId(cot_id)})
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    # Solo el ejecutivo dueño puede editar
    if cot["ejecutivo_id"] != ejecutivo_id:
        raise HTTPException(status_code=403, detail="No autorizado para editar esta cotización")

    if cot["estado"] not in (EstadoCotizacion.borrador, EstadoCotizacion.enviada):
        raise HTTPException(status_code=400, detail="Solo se pueden editar cotizaciones en borrador o enviadas")

    updates = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "estado"}

    # Recalcular si cambian productos o parámetros
    if "productos" in updates or "parametros" in updates:
        productos = updates.get("productos", cot["productos"])
        parametros = updates.get("parametros", cot["parametros"])
        costos = await db.costos_fijos.find({"activo": True}).to_list(None)
        costos_total = sum(c["valor_mensual"] for c in costos)
        updates["calculos"] = calcular(productos, parametros, costos_total)

    updates["actualizado_en"] = datetime.utcnow()
    await db.cotizaciones.update_one({"_id": ObjectId(cot_id)}, {"$set": updates})
    return await db.cotizaciones.find_one({"_id": ObjectId(cot_id)})


async def cambiar_estado(
    db: AsyncIOMotorDatabase,
    cot_id: str,
    nuevo_estado: EstadoCotizacion,
    ejecutivo_id: ObjectId,
) -> dict:
    cot = await db.cotizaciones.find_one({"_id": ObjectId(cot_id)})
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    estado_actual = EstadoCotizacion(cot["estado"])
    if nuevo_estado not in TRANSICIONES_VALIDAS.get(estado_actual, set()):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede pasar de '{estado_actual}' a '{nuevo_estado}'"
        )

    update = {
        "estado": nuevo_estado,
        "actualizado_en": datetime.utcnow(),
    }

    # Al aprobar → crear compra automáticamente
    if nuevo_estado == EstadoCotizacion.aprobada:
        await _iniciar_proceso_compra(db, cot)

    await db.cotizaciones.update_one({"_id": ObjectId(cot_id)}, {"$set": update})
    return await db.cotizaciones.find_one({"_id": ObjectId(cot_id)})


async def _iniciar_proceso_compra(db: AsyncIOMotorDatabase, cot: dict):
    """Crea el documento compra y sus compra_items cuando se aprueba la cotización."""
    cot_id = cot["_id"]

    compra_doc = {
        "cotizacion_id": cot_id,
        "estado": "pendiente",
        "iniciada_en": datetime.utcnow(),
        "completada_en": None,
        "total_pagado": 0,
        "notas": "",
    }
    compra_result = await db.compras.insert_one(compra_doc)
    compra_id = compra_result.inserted_id

    # Un compra_item por cada producto
    items = []
    for producto in cot.get("productos", []):
        items.append({
            "compra_id": compra_id,
            "cotizacion_id": cot_id,
            "producto_idx": producto["idx"],
            "producto_desc": producto["desc"],
            "cantidad_total": producto["cantidad"],
            "cantidad_comprada": 0,
            "parciales": [],
        })

    if items:
        await db.compra_items.insert_many(items)
