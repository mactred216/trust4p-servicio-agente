import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

registro = logging.getLogger("trust4p.indices")

ASC, DESC = 1, -1

# Diccionario de Datos, hoja 3. El indice vectorial de fragmentos_conocimiento
# (ASR-15) es un indice de Atlas Search y se administra aparte.
INDICES: list[tuple[str, list[tuple[str, int]], dict]] = [
    ("documentos_conocimiento", [("categoria", ASC), ("activo", ASC)], {}),
    ("fragmentos_conocimiento", [("documento_id", ASC), ("activo", ASC)], {}),
    ("ejecuciones_agente", [("diagnostico_id", ASC), ("ejecutado_en", ASC)], {}),
    ("ejecuciones_agente", [("estado", ASC)], {}),
]


async def crear_indices(db: AsyncIOMotorDatabase) -> list[str]:
    """Idempotente. Un indice que no se pueda crear se registra y se devuelve,
    sin detener el arranque del servicio."""
    problemas = []
    for coleccion, claves, opciones in INDICES:
        try:
            await db[coleccion].create_index(claves, **opciones)
        except Exception as e:
            descripcion = f"{coleccion}{[c for c, _ in claves]}: {e}"
            registro.warning("No se pudo crear el indice %s", descripcion)
            problemas.append(descripcion)
    return problemas
