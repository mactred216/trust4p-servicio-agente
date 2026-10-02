from unittest.mock import AsyncMock, MagicMock

import pytest

from src.aplicacion.casos_uso.gestionar_base_conocimiento import (
    ActualizarDocumento, CargarDocumento, DesactivarDocumento,
    DocumentoNoEncontrado, ListarDocumentos, ReactivarDocumento,
    fragmentar_texto)
from src.dominio.entidades.documento_conocimiento import DocumentoConocimiento


def crear_documento_prueba(id="doc-1", activo=True) -> DocumentoConocimiento:
    return DocumentoConocimiento(
        id=id,
        titulo="Rúbrica de madurez",
        categoria="rubrica",
        version="1.0",
        cargado_por="admin-1",
        activo=activo,
    )


def crear_mocks():
    repo_documento = AsyncMock()
    repo_fragmento = AsyncMock()
    extractor = MagicMock()
    embeddings = AsyncMock()
    embeddings.generar.return_value = [0.1, 0.2, 0.3]
    return repo_documento, repo_fragmento, extractor, embeddings


def test_fragmentar_texto_respeta_tamano_aproximado():
    """1.600 caracteres con solapamiento de 200, según lo especificado en
    el documento del proyecto."""
    texto = " ".join(f"palabra{i}" for i in range(1000)) + "."
    partes = fragmentar_texto(texto)
    assert len(partes) > 1
    for parte in partes:
        assert len(parte) <= 1600


def test_fragmentar_texto_vacio_no_produce_fragmentos():
    assert fragmentar_texto("") == []


@pytest.mark.asyncio
async def test_cargar_documento_categoria_invalida_falla():
    repo_documento, repo_fragmento, extractor, embeddings = crear_mocks()
    caso_uso = CargarDocumento(repo_documento, repo_fragmento, extractor, embeddings)

    with pytest.raises(ValueError):
        await caso_uso.ejecutar(
            cargado_por="admin-1",
            titulo="X",
            categoria="no-es-una-categoria",
            version="1.0",
            contenido_archivo=b"contenido",
        )
    repo_documento.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_cargar_documento_sin_texto_extraible_falla():
    repo_documento, repo_fragmento, extractor, embeddings = crear_mocks()
    extractor.extraer.return_value = "   "
    caso_uso = CargarDocumento(repo_documento, repo_fragmento, extractor, embeddings)

    with pytest.raises(ValueError):
        await caso_uso.ejecutar(
            cargado_por="admin-1",
            titulo="X",
            categoria="rubrica",
            version="1.0",
            contenido_archivo=b"contenido",
        )


@pytest.mark.asyncio
async def test_cargar_documento_exitoso_genera_fragmentos_vectorizados():
    repo_documento, repo_fragmento, extractor, embeddings = crear_mocks()
    extractor.extraer.return_value = "texto de prueba con contenido real."
    repo_documento.guardar.side_effect = lambda d: (setattr(d, "id", "doc-nuevo") or d)
    caso_uso = CargarDocumento(repo_documento, repo_fragmento, extractor, embeddings)

    documento = await caso_uso.ejecutar(
        cargado_por="admin-1",
        titulo="Rúbrica",
        categoria="rubrica",
        version="1.0",
        contenido_archivo=b"contenido",
    )

    assert documento.id == "doc-nuevo"
    repo_fragmento.guardar_lote.assert_called_once()
    fragmentos_guardados = repo_fragmento.guardar_lote.call_args[0][0]
    assert len(fragmentos_guardados) == 1
    assert fragmentos_guardados[0].documento_id == "doc-nuevo"
    assert fragmentos_guardados[0].embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_actualizar_documento_inexistente_falla():
    repo_documento, repo_fragmento, extractor, embeddings = crear_mocks()
    repo_documento.obtener_por_id.return_value = None
    caso_uso = ActualizarDocumento(
        repo_documento, repo_fragmento, extractor, embeddings
    )

    with pytest.raises(DocumentoNoEncontrado):
        await caso_uso.ejecutar(
            cargado_por="admin-1",
            documento_id="no-existe",
            version="2.0",
            contenido_archivo=b"contenido",
        )


@pytest.mark.asyncio
async def test_actualizar_documento_crea_nueva_version_y_desactiva_anterior():
    repo_documento, repo_fragmento, extractor, embeddings = crear_mocks()
    anterior = crear_documento_prueba(id="doc-1")
    repo_documento.obtener_por_id.return_value = anterior
    extractor.extraer.return_value = "contenido nuevo de la version 2."
    repo_documento.guardar.side_effect = lambda d: (setattr(d, "id", "doc-2") or d)
    caso_uso = ActualizarDocumento(
        repo_documento, repo_fragmento, extractor, embeddings
    )

    nuevo = await caso_uso.ejecutar(
        cargado_por="admin-1",
        documento_id="doc-1",
        version="2.0",
        contenido_archivo=b"contenido",
    )

    assert nuevo.id == "doc-2"
    assert nuevo.version == "2.0"
    assert (
        nuevo.titulo == anterior.titulo
    )  # conserva el título si no se envía uno nuevo
    assert anterior.activo is False  # la version anterior queda desactivada
    repo_documento.actualizar.assert_called_once_with(anterior)
    repo_fragmento.desactivar_por_documento.assert_called_once_with("doc-1")


@pytest.mark.asyncio
async def test_desactivar_documento():
    repo_documento = AsyncMock()
    repo_fragmento = AsyncMock()
    documento = crear_documento_prueba()
    repo_documento.obtener_por_id.return_value = documento
    caso_uso = DesactivarDocumento(repo_documento, repo_fragmento)

    resultado = await caso_uso.ejecutar("doc-1")

    assert resultado.activo is False
    repo_fragmento.desactivar_por_documento.assert_called_once_with("doc-1")


@pytest.mark.asyncio
async def test_desactivar_documento_inexistente_falla():
    repo_documento = AsyncMock()
    repo_fragmento = AsyncMock()
    repo_documento.obtener_por_id.return_value = None
    caso_uso = DesactivarDocumento(repo_documento, repo_fragmento)

    with pytest.raises(DocumentoNoEncontrado):
        await caso_uso.ejecutar("no-existe")


@pytest.mark.asyncio
async def test_reactivar_documento():
    repo_documento = AsyncMock()
    repo_fragmento = AsyncMock()
    documento = crear_documento_prueba(activo=False)
    repo_documento.obtener_por_id.return_value = documento
    caso_uso = ReactivarDocumento(repo_documento, repo_fragmento)

    resultado = await caso_uso.ejecutar("doc-1")

    assert resultado.activo is True
    repo_fragmento.reactivar_por_documento.assert_called_once_with("doc-1")


@pytest.mark.asyncio
async def test_listar_documentos():
    repo_documento = AsyncMock()
    repo_documento.listar.return_value = [crear_documento_prueba()]
    caso_uso = ListarDocumentos(repo_documento)

    resultado = await caso_uso.ejecutar()

    assert len(resultado) == 1
