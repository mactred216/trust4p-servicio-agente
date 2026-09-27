from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento
from src.dominio.puertos.repositorio_fragmento_conocimiento import \
    RepositorioFragmentoConocimiento

NOMBRE_INDICE_VECTORIAL = "vector_index"


class RepositorioMongoFragmentoConocimiento(RepositorioFragmentoConocimiento):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["fragmentos_conocimiento"]

    async def guardar_lote(self, fragmentos: list[FragmentoConocimiento]) -> None:
        if not fragmentos:
            return
        await self._coleccion.insert_many([self._a_documento(f) for f in fragmentos])

    async def buscar_por_similitud(
        self,
        embedding: list[float],
        categoria: Optional[str] = None,
        limite: int = 5,
    ) -> list[FragmentoConocimiento]:
        # El índice vectorial de Atlas solo declara el campo 'embedding' como
        # campo de filtro disponible (no 'categoria' ni 'activo'), así que el
        # filtrado por esos dos campos se hace en una etapa $match posterior,
        # no dentro de $vectorSearch — con un numCandidates generoso para que
        # el post-filtrado no deje el resultado corto.
        etapa_match: dict = {"activo": True}
        if categoria is not None:
            etapa_match["categoria"] = categoria

        pipeline = [
            {
                "$vectorSearch": {
                    "index": NOMBRE_INDICE_VECTORIAL,
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": max(limite * 20, 100),
                    "limit": limite * 5,
                }
            },
            {"$match": etapa_match},
            {"$limit": limite},
        ]
        documentos = await self._coleccion.aggregate(pipeline).to_list(length=limite)
        return [self._a_entidad(doc) for doc in documentos]

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
