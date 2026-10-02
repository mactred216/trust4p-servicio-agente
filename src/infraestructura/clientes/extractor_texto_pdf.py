from langchain_community.document_loaders.parsers import PyPDFParser
from langchain_core.documents.base import Blob

from src.dominio.puertos.extractor_texto import ExtractorTexto


class ExtractorTextoPDF(ExtractorTexto):
    """RF-41 paso 1: formato permitido = PDF. Usa el cargador de documentos
    de LangChain sobre el contenido en memoria (Blob) — no necesita
    escribir un archivo temporal en disco."""

    def extraer(self, contenido: bytes) -> str:
        parser = PyPDFParser()
        blob = Blob.from_data(contenido)
        paginas = [documento.page_content for documento in parser.lazy_parse(blob)]
        return "\n\n".join(paginas)
