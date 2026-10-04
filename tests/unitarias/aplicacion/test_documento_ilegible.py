from unittest.mock import AsyncMock, MagicMock

import pytest

from src.aplicacion.casos_uso.gestionar_base_conocimiento import (
    ActualizarDocumento, CargarDocumento, DocumentoIlegible)
from src.dominio.entidades.documento_conocimiento import DocumentoConocimiento


def armar(extractor):
    repo_documento = AsyncMock()
    repo_fragmento = AsyncMock()
    embeddings = AsyncMock()
    return repo_documento, repo_fragmento, embeddings, extractor


def extractor_que_falla():
    extractor = MagicMock()
    extractor.extraer.side_effect = RuntimeError("EOF marker not found")
    return extractor


@pytest.mark.asyncio
async def test_un_pdf_corrupto_se_reporta_como_documento_ilegible_y_no_guarda_nada():
    """RNF-07: error de validacion, no un fallo interno; sin documentos a medias."""
    repo_documento, repo_fragmento, embeddings, extractor = armar(extractor_que_falla())

    with pytest.raises(DocumentoIlegible):
        await CargarDocumento(
            repo_documento, repo_fragmento, extractor, embeddings
        ).ejecutar("adm", "T", "rubrica", "1", b"basura")

    repo_documento.guardar.assert_not_called()
    repo_fragmento.guardar_lote.assert_not_called()
    embeddings.generar.assert_not_called()


@pytest.mark.asyncio
async def test_actualizar_con_un_pdf_corrupto_deja_intacta_la_version_anterior():
    repo_documento, repo_fragmento, embeddings, extractor = armar(extractor_que_falla())
    anterior = DocumentoConocimiento(
        id="d1", titulo="T", categoria="rubrica", version="1", cargado_por="adm"
    )
    repo_documento.obtener_por_id.return_value = anterior

    with pytest.raises(DocumentoIlegible):
        await ActualizarDocumento(
            repo_documento, repo_fragmento, extractor, embeddings
        ).ejecutar("adm", "d1", "2", b"basura")

    assert anterior.activo is True
    repo_documento.guardar.assert_not_called()
    repo_fragmento.desactivar_por_documento.assert_not_called()


def test_documento_ilegible_es_un_value_error():
    assert issubclass(DocumentoIlegible, ValueError)
