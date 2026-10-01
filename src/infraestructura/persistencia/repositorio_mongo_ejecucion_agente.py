from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.ejecucion_agente import EjecucionAgente
from src.dominio.puertos.repositorio_ejecucion_agente import \
    RepositorioEjecucionAgente


class RepositorioMongoEjecucionAgente(RepositorioEjecucionAgente):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["ejecuciones_agente"]

    async def registrar(self, ejecucion: EjecucionAgente) -> EjecucionAgente:
        doc = {
            "diagnostico_id": ejecucion.diagnostico_id,
            "intento": ejecucion.intento,
            "peticion": ejecucion.peticion,
            "fragmentos_recuperados": ejecucion.fragmentos_recuperados,
            "proveedor": ejecucion.proveedor,
            "modelo": ejecucion.modelo,
            "version_prompt": ejecucion.version_prompt,
            "modelo_version": ejecucion.modelo_version,
            "estado": ejecucion.estado,
            "respuesta": ejecucion.respuesta,
            "mensaje_error": ejecucion.mensaje_error,
            "tokens_entrada": ejecucion.tokens_entrada,
            "tokens_salida": ejecucion.tokens_salida,
            "duracion_ms": ejecucion.duracion_ms,
            "ejecutado_en": ejecucion.ejecutado_en,
        }
        resultado = await self._coleccion.insert_one(doc)
        ejecucion.id = str(resultado.inserted_id)
        return ejecucion

    async def listar_por_diagnostico(
        self, diagnostico_id: str
    ) -> list[EjecucionAgente]:
        cursor = self._coleccion.find({"diagnostico_id": diagnostico_id}).sort(
            "intento", 1
        )
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> EjecucionAgente:
        return EjecucionAgente(
            id=str(doc["_id"]),
            diagnostico_id=doc["diagnostico_id"],
            intento=doc["intento"],
            peticion=doc["peticion"],
            fragmentos_recuperados=doc["fragmentos_recuperados"],
            proveedor=doc["proveedor"],
            modelo=doc["modelo"],
            version_prompt=doc["version_prompt"],
            modelo_version=doc["modelo_version"],
            estado=doc["estado"],
            respuesta=doc.get("respuesta"),
            mensaje_error=doc.get("mensaje_error"),
            tokens_entrada=doc.get("tokens_entrada"),
            tokens_salida=doc.get("tokens_salida"),
            duracion_ms=doc.get("duracion_ms"),
            ejecutado_en=doc["ejecutado_en"],
        )
