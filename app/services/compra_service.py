from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from app.schemas.compra import ParcialCreate, EstadoCompra
from app.schemas.cotizacion import EstadoCotizacion


async def agregar_parcial(
    db: AsyncIOMotorDatabase,
    item_id: str,
    parcial: ParcialCreate,
) -> dict:
    """Agrega una compra parcial a un compra_item."""
    item = await db.compra_items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item de compra no encontrado")

    parcial_dict = parcial.model_dump()
    parcial_dict["total"] = round(parcial.cantidad * parcial.precio_unit, 0)
    parcial_dict["fecha"] = parcial.fecha or datetime.utcnow()

    nueva_cantidad = item["cantidad_comprada"] + parcial.cantidad
    if nueva_cantidad > item["cantidad_total"]:
        raise HTTPException(
            status_code=400,
            detail=f"La cantidad supera el total requerido ({item['cantidad_total']})"
        )

    await db.compra_items.update_one(
        {"_id": ObjectId(item_id)},
        {
            "$push": {"parciales": parcial_dict},
            "$set": {"cantidad_comprada": nueva_cantidad},
        }
    )

    # Recalcular total pagado en la compra
    await _recalcular_total_compra(db, item["compra_id"])

    # Verificar si todos los items están completos
    await _verificar_compra_completa(db, item["compra_id"], item["cotizacion_id"])

    return await db.compra_items.find_one({"_id": ObjectId(item_id)})


async def _recalcular_total_compra(db: AsyncIOMotorDatabase, compra_id: ObjectId):
    """Suma todos los parciales de todos los items para actualizar total_pagado."""
    pipeline = [
        {"$match": {"compra_id": compra_id}},
        {"$unwind": {"path": "$parciales", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": None, "total": {"$sum": "$parciales.total"}}},
    ]
    result = await db.compra_items.aggregate(pipeline).to_list(1)
    total = result[0]["total"] if result else 0

    await db.compras.update_one(
        {"_id": compra_id},
        {"$set": {"total_pagado": total, "estado": EstadoCompra.en_progreso}}
    )


async def _verificar_compra_completa(
    db: AsyncIOMotorDatabase,
    compra_id: ObjectId,
    cotizacion_id: ObjectId,
):
    """Si todos los items están completos, cierra la compra y actualiza la cotización."""
    items = await db.compra_items.find({"compra_id": compra_id}).to_list(None)
    todos_completos = all(
        i["cantidad_comprada"] >= i["cantidad_total"] for i in items
    )

    if todos_completos:
        await db.compras.update_one(
            {"_id": compra_id},
            {"$set": {
                "estado": EstadoCompra.completada,
                "completada_en": datetime.utcnow(),
            }}
        )
        await db.cotizaciones.update_one(
            {"_id": cotizacion_id},
            {"$set": {"estado": EstadoCotizacion.comprada}}
        )


async def _sincronizar_item_y_compra(db: AsyncIOMotorDatabase, item_id: ObjectId):
    """Recalcula cantidad_comprada, total_pagado y estados tras modificar parciales."""
    item = await db.compra_items.find_one({"_id": item_id})
    compra_id = item["compra_id"]
    cotizacion_id = item["cotizacion_id"]

    nueva_cantidad = sum(p["cantidad"] for p in item.get("parciales", []))
    await db.compra_items.update_one(
        {"_id": item_id}, {"$set": {"cantidad_comprada": nueva_cantidad}}
    )

    pipeline = [
        {"$match": {"compra_id": compra_id}},
        {"$unwind": {"path": "$parciales", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": None, "total": {"$sum": "$parciales.total"}}},
    ]
    result = await db.compra_items.aggregate(pipeline).to_list(1)
    total = result[0]["total"] if result else 0

    all_items = await db.compra_items.find({"compra_id": compra_id}).to_list(None)
    todos_completos = all(
        (nueva_cantidad if str(i["_id"]) == str(item_id) else i["cantidad_comprada"]) >= i["cantidad_total"]
        for i in all_items
    )

    if todos_completos:
        await db.compras.update_one(
            {"_id": compra_id},
            {"$set": {"total_pagado": total, "estado": EstadoCompra.completada, "completada_en": datetime.utcnow()}},
        )
        await db.cotizaciones.update_one({"_id": cotizacion_id}, {"$set": {"estado": EstadoCotizacion.comprada}})
    else:
        await db.compras.update_one(
            {"_id": compra_id},
            {"$set": {"total_pagado": total, "estado": EstadoCompra.en_progreso}, "$unset": {"completada_en": ""}},
        )
        cot = await db.cotizaciones.find_one({"_id": cotizacion_id})
        if cot and cot.get("estado") == EstadoCotizacion.comprada:
            await db.cotizaciones.update_one({"_id": cotizacion_id}, {"$set": {"estado": EstadoCotizacion.en_compra}})


async def eliminar_parcial(db: AsyncIOMotorDatabase, item_id: str, parcial_idx: int) -> dict:
    item = await db.compra_items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    if parcial_idx < 0 or parcial_idx >= len(item.get("parciales", [])):
        raise HTTPException(status_code=404, detail="Parcial no encontrado")

    await db.compra_items.update_one(
        {"_id": ObjectId(item_id)}, {"$unset": {f"parciales.{parcial_idx}": 1}}
    )
    await db.compra_items.update_one(
        {"_id": ObjectId(item_id)}, {"$pull": {"parciales": None}}
    )
    await _sincronizar_item_y_compra(db, ObjectId(item_id))
    return await db.compra_items.find_one({"_id": ObjectId(item_id)})


async def actualizar_parcial(db: AsyncIOMotorDatabase, item_id: str, parcial_idx: int, data) -> dict:
    item = await db.compra_items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    parciales = item.get("parciales", [])
    if parcial_idx < 0 or parcial_idx >= len(parciales):
        raise HTTPException(status_code=404, detail="Parcial no encontrado")

    if data.cantidad is not None:
        otras = sum(p["cantidad"] for i, p in enumerate(parciales) if i != parcial_idx)
        if otras + data.cantidad > item["cantidad_total"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cantidad excede el total requerido ({item['cantidad_total']})",
            )

    parc = dict(parciales[parcial_idx])
    update = {}
    if data.proveedor is not None:
        update[f"parciales.{parcial_idx}.proveedor"] = data.proveedor
        parc["proveedor"] = data.proveedor
    if data.cantidad is not None:
        update[f"parciales.{parcial_idx}.cantidad"] = data.cantidad
        parc["cantidad"] = data.cantidad
    if data.precio_unit is not None:
        update[f"parciales.{parcial_idx}.precio_unit"] = data.precio_unit
        parc["precio_unit"] = data.precio_unit
    if data.notas is not None:
        update[f"parciales.{parcial_idx}.notas"] = data.notas
    update[f"parciales.{parcial_idx}.total"] = round(parc["cantidad"] * parc["precio_unit"], 0)

    await db.compra_items.update_one({"_id": ObjectId(item_id)}, {"$set": update})
    await _sincronizar_item_y_compra(db, ObjectId(item_id))
    return await db.compra_items.find_one({"_id": ObjectId(item_id)})


async def get_compra_con_items(db: AsyncIOMotorDatabase, cotizacion_id: str) -> dict:
    """Devuelve la compra con todos sus items para la vista de logística."""
    compra = await db.compras.find_one({"cotizacion_id": ObjectId(cotizacion_id)})
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    items = await db.compra_items.find(
        {"compra_id": compra["_id"]}
    ).sort("producto_idx", 1).to_list(None)

    # Añadir campo calculado 'completo'
    for item in items:
        item["completo"] = item["cantidad_comprada"] >= item["cantidad_total"]
        item["_id"] = str(item["_id"])
        item["compra_id"] = str(item["compra_id"])
        item["cotizacion_id"] = str(item["cotizacion_id"])

    compra["_id"] = str(compra["_id"])
    compra["cotizacion_id"] = str(compra["cotizacion_id"])
    compra["items"] = items
    return compra
