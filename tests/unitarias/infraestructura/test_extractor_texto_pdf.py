import io

from pypdf import PdfWriter

from src.infraestructura.clientes.extractor_texto_pdf import ExtractorTextoPDF


def crear_pdf_prueba(paginas: int = 2) -> bytes:
    escritor = PdfWriter()
    for _ in range(paginas):
        escritor.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    escritor.write(buffer)
    return buffer.getvalue()


def test_extraer_no_falla_con_pdf_valido():
    extractor = ExtractorTextoPDF()
    texto = extractor.extraer(crear_pdf_prueba(paginas=2))
    assert isinstance(texto, str)


def test_extraer_conserva_separador_entre_paginas():
    extractor = ExtractorTextoPDF()
    texto = extractor.extraer(crear_pdf_prueba(paginas=3))
    assert texto.count("\n\n") == 2  # 3 páginas -> 2 separadores
