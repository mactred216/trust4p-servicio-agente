from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento
from src.dominio.puertos.repositorio_fragmento_conocimiento import \
    RepositorioFragmentoConocimiento


class RepositorioMongoFragmentoConocimiento(RepositorioFragmentoConocimiento):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["fragmentos_conocimiento"]

    async def guardar_lote(self, fragmentos: list[FragmentoConocimiento]) -> None:
        if not fragmentos:
            return
        await self._coleccion.insert_many([self._a_documento(f) for f in fragmentos])

    async def listar_por_documento(
        self, documento_id: str
    ) -> list[FragmentoConocimiento]:
        cursor = self._coleccion.find({"documento_id": documento_id}).sort("orden", 1)
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    async def desactivar_por_documento(self, documento_id: str) -> None:
        await self._coleccion.update_many(
            {"documento_id": documento_id}, {"$set": {"activo": False}}
        )

    async def reactivar_por_documento(self, documento_id: str) -> None:
        await self._coleccion.update_many(
            {"documento_id": documento_id}, {"$set": {"activo": True}}
        )

    def _a_entidad(self, doc: dict) -> FragmentoConocimiento:
        return FragmentoConocimiento(
            id=str(doc["_id"]),
            documento_id=doc["documento_id"],
            categoria=doc["categoria"],
            orden=doc["orden"],
            contenido=doc["contenido"],
            embedding=doc["embedding"],
            tokens=doc.get("tokens"),
            activo=doc.get("activo", True),
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, fragmento: FragmentoConocimiento) -> dict:
        return {
            "documento_id": fragmento.documento_id,
            "categoria": fragmento.categoria,
            "orden": fragmento.orden,
            "contenido": fragmento.contenido,
            "embedding": fragmento.embedding,
            "tokens": fragmento.tokens,
            "activo": fragmento.activo,
            "creado_en": fragmento.creado_en,
        }
