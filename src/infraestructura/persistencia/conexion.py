import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_cliente: AsyncIOMotorClient | None = None


def obtener_cliente() -> AsyncIOMotorClient:
    global _cliente
    if _cliente is None:
        _cliente = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    return _cliente


def obtener_base_datos() -> AsyncIOMotorDatabase:
    """Misma base de datos ('trust4p') que trust4p-api-negocio. Este
    servicio lee/escribe documentos_conocimiento y fragmentos_conocimiento,
    y lee (solo lectura) sesiones — nunca toca las colecciones
    transaccionales propias del servicio de negocio."""
    return obtener_cliente()["trust4p"]
