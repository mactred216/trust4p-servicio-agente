from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.documento_conocimiento import DocumentoConocimiento
from src.dominio.puertos.repositorio_documento_conocimiento import \
    RepositorioDocumentoConocimiento


class RepositorioMongoDocumentoConocimiento(RepositorioDocumentoConocimiento):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["documentos_conocimiento"]

    async def guardar(self, documento: DocumentoConocimiento) -> DocumentoConocimiento:
        doc = self._a_documento(documento)
        resultado = await self._coleccion.insert_one(doc)
        documento.id = str(resultado.inserted_id)
        return documento

    async def obtener_por_id(
        self, documento_id: str
    ) -> Optional[DocumentoConocimiento]:
        try:
            id_valido = ObjectId(documento_id)
        except InvalidId:
            return None
        doc = await self._coleccion.find_one({"_id": id_valido})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def actualizar(self, documento: DocumentoConocimiento) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(documento.id)},
            {"$set": self._a_documento(documento)},
        )

    async def listar(self) -> list[DocumentoConocimiento]:
        cursor = self._coleccion.find().sort("creado_en", -1)
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> DocumentoConocimiento:
        return DocumentoConocimiento(
            id=str(doc["_id"]),
            titulo=doc["titulo"],
            categoria=doc["categoria"],
            version=doc["version"],
            cargado_por=doc["cargado_por"],
            fuente=doc.get("fuente"),
            activo=doc.get("activo", True),
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, documento: DocumentoConocimiento) -> dict:
        return {
            "titulo": documento.titulo,
            "categoria": documento.categoria,
            "version": documento.version,
            "cargado_por": documento.cargado_por,
            "fuente": documento.fuente,
            "activo": documento.activo,
            "creado_en": documento.creado_en,
        }
