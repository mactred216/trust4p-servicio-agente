import pytest

from src.dominio.entidades.ejecucion_agente import EjecucionAgente
from src.infraestructura.persistencia.repositorio_mongo_ejecucion_agente import \
    RepositorioMongoEjecucionAgente


def crear_ejecucion_prueba(estado="exitosa") -> EjecucionAgente:
    return EjecucionAgente(
        id=None,
        diagnostico_id="diag-1",
        intento=1,
        peticion={"empresa_id": "emp-1"},
        fragmentos_recuperados=["f1", "f2"],
        modelo_lenguaje_id="qwen3-next-80b-a3b-instruct-maas",
        version_plantilla_instrucciones="1.0",
        estado=estado,
        respuesta={"sintesis": "..."} if estado == "exitosa" else None,
        motivo_fallo=None if estado == "exitosa" else "esquema inválido",
    )


@pytest.mark.asyncio
async def test_registrar_asigna_id(db):
    repo = RepositorioMongoEjecucionAgente(db)
    ejecucion = await repo.registrar(crear_ejecucion_prueba())
    assert ejecucion.id is not None


@pytest.mark.asyncio
async def test_registrar_persiste_los_datos(db):
    repo = RepositorioMongoEjecucionAgente(db)
    await repo.registrar(crear_ejecucion_prueba(estado="fallida"))

    doc = await db["ejecuciones_agente"].find_one({"diagnostico_id": "diag-1"})

    assert doc is not None
    assert doc["estado"] == "fallida"
    assert doc["motivo_fallo"] == "esquema inválido"
    assert doc["fragmentos_recuperados"] == ["f1", "f2"]
