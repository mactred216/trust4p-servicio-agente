import pytest

from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento
from src.infraestructura.persistencia.repositorio_mongo_fragmento_conocimiento import \
    RepositorioMongoFragmentoConocimiento


def crear_fragmento_prueba(documento_id="doc-1", orden=1) -> FragmentoConocimiento:
    return FragmentoConocimiento(
        id=None,
        documento_id=documento_id,
        categoria="rubrica",
        orden=orden,
        contenido="texto del fragmento",
        embedding=[0.1, 0.2, 0.3],
        tokens=3,
    )


@pytest.mark.asyncio
async def test_guardar_lote_y_listar_por_documento(db):
    repo = RepositorioMongoFragmentoConocimiento(db)
    await repo.guardar_lote(
        [
            crear_fragmento_prueba(orden=2),
            crear_fragmento_prueba(orden=1),
        ]
    )

    fragmentos = await repo.listar_por_documento("doc-1")

    assert len(fragmentos) == 2
    assert [f.orden for f in fragmentos] == [1, 2]  # ordenados
    assert fragmentos[0].embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_guardar_lote_vacio_no_falla(db):
    repo = RepositorioMongoFragmentoConocimiento(db)
    await repo.guardar_lote([])
    assert await repo.listar_por_documento("doc-1") == []


@pytest.mark.asyncio
async def test_desactivar_y_reactivar_por_documento(db):
    repo = RepositorioMongoFragmentoConocimiento(db)
    await repo.guardar_lote(
        [crear_fragmento_prueba(orden=1), crear_fragmento_prueba(orden=2)]
    )

    await repo.desactivar_por_documento("doc-1")
    fragmentos = await repo.listar_por_documento("doc-1")
    assert all(f.activo is False for f in fragmentos)

    await repo.reactivar_por_documento("doc-1")
    fragmentos = await repo.listar_por_documento("doc-1")
    assert all(f.activo is True for f in fragmentos)
