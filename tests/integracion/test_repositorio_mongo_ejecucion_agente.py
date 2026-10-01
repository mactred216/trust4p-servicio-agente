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
        proveedor="google-vertex-ai",
        modelo="qwen3-next-80b-a3b-instruct-maas",
        version_prompt="1.0",
        modelo_version="1",
        estado=estado,
        respuesta={"sintesis": "..."} if estado == "exitosa" else None,
        mensaje_error=None if estado == "exitosa" else "esquema inválido",
        tokens_entrada=120 if estado == "exitosa" else None,
        tokens_salida=80 if estado == "exitosa" else None,
        duracion_ms=950,
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
    assert doc["mensaje_error"] == "esquema inválido"
    assert doc["fragmentos_recuperados"] == ["f1", "f2"]
    assert doc["proveedor"] == "google-vertex-ai"
    assert doc["modelo_version"] == "1"
    assert doc["duracion_ms"] == 950


@pytest.mark.asyncio
async def test_listar_por_diagnostico_ordena_por_intento(db):
    repo = RepositorioMongoEjecucionAgente(db)
    fallida = crear_ejecucion_prueba(estado="fallida")
    fallida.intento = 1
    exitosa = crear_ejecucion_prueba(estado="exitosa")
    exitosa.intento = 2
    # Se registran en orden inverso para confirmar que el orden de la
    # consulta depende del campo 'intento', no del orden de inserción.
    await repo.registrar(exitosa)
    await repo.registrar(fallida)

    ejecuciones = await repo.listar_por_diagnostico("diag-1")

    assert [e.intento for e in ejecuciones] == [1, 2]
    assert [e.estado for e in ejecuciones] == ["fallida", "exitosa"]
    assert ejecuciones[1].respuesta == {"sintesis": "..."}
    assert ejecuciones[1].tokens_entrada == 120
    assert ejecuciones[0].mensaje_error == "esquema inválido"


@pytest.mark.asyncio
async def test_listar_por_diagnostico_sin_ejecuciones_devuelve_lista_vacia(db):
    repo = RepositorioMongoEjecucionAgente(db)
    assert await repo.listar_por_diagnostico("diag-sin-ejecuciones") == []


@pytest.mark.asyncio
async def test_listar_por_diagnostico_ignora_otros_diagnosticos(db):
    repo = RepositorioMongoEjecucionAgente(db)
    await repo.registrar(crear_ejecucion_prueba())
    otra = crear_ejecucion_prueba()
    otra.diagnostico_id = "diag-2"
    await repo.registrar(otra)

    ejecuciones = await repo.listar_por_diagnostico("diag-2")

    assert len(ejecuciones) == 1
    assert ejecuciones[0].diagnostico_id == "diag-2"
