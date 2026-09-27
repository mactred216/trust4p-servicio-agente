import pytest

from src.dominio.entidades.evaluacion import (PerfilCulturalCalculado,
                                              ResultadoCalculo,
                                              SolicitudEvaluacion)
from src.dominio.servicios.saneador import (DatoProhibidoError, sanear_payload,
                                            sanear_solicitud)


def crear_solicitud_prueba(empresa_id="emp-1") -> SolicitudEvaluacion:
    return SolicitudEvaluacion(
        diagnostico_id="diag-1",
        empresa_id=empresa_id,
        modelo_version="1",
        resultado_calculo=ResultadoCalculo(
            indice_global=6,
            nivel=2,
            nivel_nombre="En desarrollo",
            nivel_descripcion="...",
            dimensiones=[],
            perfil_cultural=PerfilCulturalCalculado(codigo="ENFP"),
        ),
        respuestas=[],
        dimensiones_modelo=[],
        niveles_modelo=[],
    )


def test_sanear_solicitud_valida_no_falla():
    sanear_solicitud(crear_solicitud_prueba())


def test_sanear_solicitud_sin_empresa_id_falla():
    with pytest.raises(DatoProhibidoError):
        sanear_solicitud(crear_solicitud_prueba(empresa_id=""))


def test_sanear_payload_elimina_claves_prohibidas():
    payload = {
        "empresa_id": "emp-1",
        "razon_social": "InnovaTech SAS",
        "nit": "900123456",
        "respuestas": [{"texto": "algo", "correo": "no@debe.estar"}],
    }
    limpio = sanear_payload(payload)
    assert "razon_social" not in limpio
    assert "nit" not in limpio
    assert limpio["empresa_id"] == "emp-1"
    assert "correo" not in limpio["respuestas"][0]
    assert limpio["respuestas"][0]["texto"] == "algo"
