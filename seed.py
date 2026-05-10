"""
Script para inicializar la BD con datos base.
Ejecutar UNA vez: python seed.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "abastecimiento_total"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EJECUTIVOS = [
    {"nombre": "Gonzalo Galvez",    "email": "ggalvezb@abastecimientototal.cl",   "telefono": "+56957987697",  "password": "at2025"},
    {"nombre": "Joel Caceres",      "email": "jcaceresf@abastecimientototal.cl",   "telefono": "+56977608781",  "password": "at2025"},
    {"nombre": "Gabriela Soto",     "email": "gsotov@abastecimientototal.cl",      "telefono": "+56995423548",  "password": "at2025"},
    {"nombre": "Felipe Valdenegro", "email": "fvaldenegro@abastecimientototal.cl", "telefono": "+56949196425",  "password": "at2025"},
]

COSTOS_FIJOS = [
    {"nombre": "Contador",  "valor_mensual": 100000, "activo": True, "orden": 1},
    {"nombre": "Servidor",  "valor_mensual": 2500,   "activo": True, "orden": 2},
    {"nombre": "Odoo",      "valor_mensual": 21000,  "activo": True, "orden": 3},
]


async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]

    # Usuarios
    print("Creando ejecutivos...")
    for ej in EJECUTIVOS:
        existing = await db.users.find_one({"email": ej["email"]})
        if existing:
            print(f"  ⚠️  {ej['email']} ya existe, se omite")
            continue
        await db.users.insert_one({
            "nombre": ej["nombre"],
            "email": ej["email"],
            "telefono": ej["telefono"],
            "rol": "ejecutivo",
            "activo": True,
            "password_hash": pwd_context.hash(ej["password"]),
        })
        print(f"  ✅ {ej['nombre']} creado")

    # Costos fijos
    print("\nCreando costos fijos...")
    count = await db.costos_fijos.count_documents({})
    if count == 0:
        await db.costos_fijos.insert_many(COSTOS_FIJOS)
        print(f"  ✅ {len(COSTOS_FIJOS)} costos fijos creados")
    else:
        print(f"  ⚠️  Ya existen {count} costos fijos, se omite")

    print("\n✅ Seed completado")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
