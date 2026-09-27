import io

from pypdf import PdfReader

from src.dominio.puertos.extractor_texto import ExtractorTexto


class ExtractorTextoPDF(ExtractorTexto):
    """RF-41 paso 1: formato permitido = PDF."""

    def extraer(self, contenido: bytes) -> str:
        lector = PdfReader(io.BytesIO(contenido))
        paginas = [pagina.extract_text() or "" for pagina in lector.pages]
        return "\n\n".join(paginas)
