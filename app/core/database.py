from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

settings = get_settings()

client: AsyncIOMotorClient = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    await create_indexes(db)
    print(f"✅ Conectado a MongoDB: {settings.mongodb_db_name}")


async def close_db():
    global client
    if client:
        client.close()
        print("🔌 Conexión a MongoDB cerrada")


def get_db() -> AsyncIOMotorDatabase:
    return client[settings.mongodb_db_name]


async def create_indexes(db: AsyncIOMotorDatabase):
    """Crea índices necesarios para performance."""

    # users
    await db.users.create_index("email", unique=True)

    # cotizaciones
    await db.cotizaciones.create_index("numero", unique=True)
    await db.cotizaciones.create_index("ejecutivo_id")
    await db.cotizaciones.create_index("estado")
    await db.cotizaciones.create_index("creado_en")
    await db.cotizaciones.create_index([("estado", 1), ("creado_en", -1)])

    # compras
    await db.compras.create_index("cotizacion_id", unique=True)
    await db.compras.create_index("estado")

    # compra_items
    await db.compra_items.create_index("compra_id")
    await db.compra_items.create_index("cotizacion_id")

    # documentos
    await db.documentos.create_index([("cotizacion_id", 1), ("tipo", 1)])
    await db.documentos.create_index("subido_en")

    print("✅ Índices creados")
