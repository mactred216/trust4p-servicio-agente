import pytest

from src.dominio.entidades.documento_conocimiento import DocumentoConocimiento
from src.infraestructura.persistencia.repositorio_mongo_documento_conocimiento import \
    RepositorioMongoDocumentoConocimiento


def crear_documento_prueba(titulo="Rúbrica") -> DocumentoConocimiento:
    return DocumentoConocimiento(
        id=None,
        titulo=titulo,
        categoria="rubrica",
        version="1.0",
        cargado_por="admin-1",
        fuente="Documento de tesis",
    )


@pytest.mark.asyncio
async def test_guardar_y_obtener_por_id(db):
    repo = RepositorioMongoDocumentoConocimiento(db)
    documento = await repo.guardar(crear_documento_prueba())

    recuperado = await repo.obtener_por_id(documento.id)

    assert recuperado is not None
    assert recuperado.titulo == "Rúbrica"
    assert recuperado.activo is True


@pytest.mark.asyncio
async def test_actualizar_persiste_desactivacion(db):
    repo = RepositorioMongoDocumentoConocimiento(db)
    documento = await repo.guardar(crear_documento_prueba())

    documento.desactivar()
    await repo.actualizar(documento)

    recuperado = await repo.obtener_por_id(documento.id)
    assert recuperado.activo is False


@pytest.mark.asyncio
async def test_listar_ordena_por_mas_reciente(db):
    repo = RepositorioMongoDocumentoConocimiento(db)
    await repo.guardar(crear_documento_prueba("Primero"))
    await repo.guardar(crear_documento_prueba("Segundo"))

    documentos = await repo.listar()

    assert [d.titulo for d in documentos] == ["Segundo", "Primero"]


@pytest.mark.asyncio
async def test_obtener_por_id_con_formato_invalido_devuelve_none(db):
    repo = RepositorioMongoDocumentoConocimiento(db)
    assert await repo.obtener_por_id("no-es-un-object-id") is None
