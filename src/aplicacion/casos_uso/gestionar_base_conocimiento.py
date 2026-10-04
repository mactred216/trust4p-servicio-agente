from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.dominio.entidades.documento_conocimiento import (
    CATEGORIAS_VALIDAS, DocumentoConocimiento)
from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento
from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings
from src.dominio.puertos.extractor_texto import ExtractorTexto
from src.dominio.puertos.repositorio_documento_conocimiento import \
    RepositorioDocumentoConocimiento
from src.dominio.puertos.repositorio_fragmento_conocimiento import \
    RepositorioFragmentoConocimiento

# Fragmentación de 1.600 caracteres con solapamiento de 200 (especificado
# en el documento del proyecto). El Diccionario de Datos describe el mismo
# fragmento de forma aproximada en unidades léxicas ("200 a 400"), que es
# consistente con este tamaño en caracteres para texto en español — no son
# dos reglas distintas, la del diccionario es una anotación cualitativa de
# lo que produce esta.
TAMANO_FRAGMENTO_CARACTERES = 1600
SUPERPOSICION_CARACTERES = 200


def fragmentar_texto(texto: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TAMANO_FRAGMENTO_CARACTERES,
        chunk_overlap=SUPERPOSICION_CARACTERES,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [parte for parte in splitter.split_text(texto) if parte.strip()]


class DocumentoNoEncontrado(Exception):
    pass


class DocumentoIlegible(ValueError):
    """El archivo no se pudo leer como PDF (corrupto o con otro contenido)."""


def _extraer_texto(extractor: ExtractorTexto, contenido: bytes) -> str:
    """RNF-07: un archivo corrupto se reporta como error de validacion (422),
    nunca como un fallo interno, y se detecta antes de guardar nada."""
    try:
        texto = extractor.extraer(contenido)
    except Exception as e:
        raise DocumentoIlegible("El archivo no es un PDF legible") from e
    if not texto.strip():
        raise ValueError("El documento no contiene texto extraíble")
    return texto


async def _generar_y_guardar_fragmentos(
    repo_fragmento: RepositorioFragmentoConocimiento,
    cliente_embeddings: ClienteEmbeddings,
    documento: DocumentoConocimiento,
    texto: str,
) -> None:
    partes = fragmentar_texto(texto)
    fragmentos = []
    for orden, parte in enumerate(partes, start=1):
        embedding = await cliente_embeddings.generar(parte)
        fragmentos.append(
            FragmentoConocimiento(
                id=None,
                documento_id=documento.id,
                categoria=documento.categoria,
                orden=orden,
                contenido=parte,
                embedding=embedding,
                tokens=len(parte.split()),
            )
        )
    await repo_fragmento.guardar_lote(fragmentos)


class CargarDocumento:
    """RF-41 paso 1: carga un documento de referencia, lo fragmenta y
    vectoriza cada fragmento para la recuperación por similitud."""

    def __init__(
        self,
        repo_documento: RepositorioDocumentoConocimiento,
        repo_fragmento: RepositorioFragmentoConocimiento,
        extractor_texto: ExtractorTexto,
        cliente_embeddings: ClienteEmbeddings,
    ):
        self._documentos = repo_documento
        self._fragmentos = repo_fragmento
        self._extractor = extractor_texto
        self._embeddings = cliente_embeddings

    async def ejecutar(
        self,
        cargado_por: str,
        titulo: str,
        categoria: str,
        version: str,
        contenido_archivo: bytes,
        fuente: str | None = None,
    ) -> DocumentoConocimiento:
        if categoria not in CATEGORIAS_VALIDAS:
            raise ValueError(
                f"Categoría '{categoria}' inválida; debe ser una de {sorted(CATEGORIAS_VALIDAS)}"
            )

        texto = _extraer_texto(self._extractor, contenido_archivo)

        documento = DocumentoConocimiento(
            id=None,
            titulo=titulo,
            categoria=categoria,
            version=version,
            cargado_por=cargado_por,
            fuente=fuente,
        )
        documento = await self._documentos.guardar(documento)
        await _generar_y_guardar_fragmentos(
            self._fragmentos, self._embeddings, documento, texto
        )
        return documento


class ActualizarDocumento:
    """RF-41 paso 2: reemplaza el contenido de un documento existente sin
    sobreescribirlo — crea una nueva versión y desactiva la anterior (y sus
    fragmentos), conservando el historial de versiones."""

    def __init__(
        self,
        repo_documento: RepositorioDocumentoConocimiento,
        repo_fragmento: RepositorioFragmentoConocimiento,
        extractor_texto: ExtractorTexto,
        cliente_embeddings: ClienteEmbeddings,
    ):
        self._documentos = repo_documento
        self._fragmentos = repo_fragmento
        self._extractor = extractor_texto
        self._embeddings = cliente_embeddings

    async def ejecutar(
        self,
        cargado_por: str,
        documento_id: str,
        version: str,
        contenido_archivo: bytes,
        titulo: str | None = None,
        categoria: str | None = None,
        fuente: str | None = None,
    ) -> DocumentoConocimiento:
        anterior = await self._documentos.obtener_por_id(documento_id)
        if anterior is None:
            raise DocumentoNoEncontrado()

        categoria_nueva = categoria or anterior.categoria
        if categoria_nueva not in CATEGORIAS_VALIDAS:
            raise ValueError(
                f"Categoría '{categoria_nueva}' inválida; debe ser una de {sorted(CATEGORIAS_VALIDAS)}"
            )

        texto = _extraer_texto(self._extractor, contenido_archivo)

        nuevo = DocumentoConocimiento(
            id=None,
            titulo=titulo or anterior.titulo,
            categoria=categoria_nueva,
            version=version,
            cargado_por=cargado_por,
            fuente=fuente if fuente is not None else anterior.fuente,
        )
        nuevo = await self._documentos.guardar(nuevo)
        await _generar_y_guardar_fragmentos(
            self._fragmentos, self._embeddings, nuevo, texto
        )

        anterior.desactivar()
        await self._documentos.actualizar(anterior)
        await self._fragmentos.desactivar_por_documento(anterior.id)

        return nuevo


class DesactivarDocumento:
    def __init__(
        self,
        repo_documento: RepositorioDocumentoConocimiento,
        repo_fragmento: RepositorioFragmentoConocimiento,
    ):
        self._documentos = repo_documento
        self._fragmentos = repo_fragmento

    async def ejecutar(self, documento_id: str) -> DocumentoConocimiento:
        documento = await self._documentos.obtener_por_id(documento_id)
        if documento is None:
            raise DocumentoNoEncontrado()
        documento.desactivar()
        await self._documentos.actualizar(documento)
        await self._fragmentos.desactivar_por_documento(documento_id)
        return documento


class ReactivarDocumento:
    def __init__(
        self,
        repo_documento: RepositorioDocumentoConocimiento,
        repo_fragmento: RepositorioFragmentoConocimiento,
    ):
        self._documentos = repo_documento
        self._fragmentos = repo_fragmento

    async def ejecutar(self, documento_id: str) -> DocumentoConocimiento:
        documento = await self._documentos.obtener_por_id(documento_id)
        if documento is None:
            raise DocumentoNoEncontrado()
        documento.reactivar()
        await self._documentos.actualizar(documento)
        await self._fragmentos.reactivar_por_documento(documento_id)
        return documento


class ListarDocumentos:
    def __init__(self, repo_documento: RepositorioDocumentoConocimiento):
        self._documentos = repo_documento

    async def ejecutar(self) -> list[DocumentoConocimiento]:
        return await self._documentos.listar()
