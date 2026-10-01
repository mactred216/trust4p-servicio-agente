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
            "modelo_lenguaje_id": ejecucion.modelo_lenguaje_id,
            "version_plantilla_instrucciones": ejecucion.version_plantilla_instrucciones,
            "estado": ejecucion.estado,
            "respuesta": ejecucion.respuesta,
            "motivo_fallo": ejecucion.motivo_fallo,
            "creado_en": ejecucion.creado_en,
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
            modelo_lenguaje_id=doc["modelo_lenguaje_id"],
            version_plantilla_instrucciones=doc["version_plantilla_instrucciones"],
            estado=doc["estado"],
            respuesta=doc.get("respuesta"),
            motivo_fallo=doc.get("motivo_fallo"),
            creado_en=doc["creado_en"],
        )
