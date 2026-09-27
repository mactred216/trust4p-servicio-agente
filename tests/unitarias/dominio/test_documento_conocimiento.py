import pytest

from src.dominio.entidades.documento_conocimiento import DocumentoConocimiento


def crear_documento_prueba(activo=True) -> DocumentoConocimiento:
    return DocumentoConocimiento(
        id="doc-1",
        titulo="Rúbrica de madurez",
        categoria="rubrica",
        version="1.0",
        cargado_por="admin-1",
        activo=activo,
    )


def test_desactivar():
    documento = crear_documento_prueba()
    documento.desactivar()
    assert documento.activo is False


def test_desactivar_ya_inactivo_falla():
    documento = crear_documento_prueba(activo=False)
    with pytest.raises(ValueError):
        documento.desactivar()


def test_reactivar():
    documento = crear_documento_prueba(activo=False)
    documento.reactivar()
    assert documento.activo is True


def test_reactivar_ya_activo_falla():
    documento = crear_documento_prueba(activo=True)
    with pytest.raises(ValueError):
        documento.reactivar()
