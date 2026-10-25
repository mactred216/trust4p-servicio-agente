from unittest.mock import MagicMock, patch

from src.infraestructura.clientes.cliente_inferencia_vertex import (
    MODELO_POR_DEFECTO, ClienteInferenciaVertex)


def test_el_modelo_por_defecto_es_uno_vigente_de_pesos_abiertos():
    """ADR-021: Qwen3-Next-80B se retiró de Vertex AI el 21-oct-2026."""
    assert "qwen" not in MODELO_POR_DEFECTO
    assert MODELO_POR_DEFECTO == "publishers/openai/models/gpt-oss-120b-maas"


def test_el_nombre_del_modelo_registrado_es_el_identificador_corto(monkeypatch):
    monkeypatch.delenv("VERTEX_INFERENCE_MODEL", raising=False)
    assert ClienteInferenciaVertex().nombre_modelo == "gpt-oss-120b-maas"


def test_el_modelo_se_puede_cambiar_por_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("VERTEX_INFERENCE_MODEL", "publishers/otro/models/modelo-x")
    assert ClienteInferenciaVertex().nombre_modelo == "modelo-x"


def test_no_se_fuerza_el_tipo_mime_de_la_respuesta(monkeypatch):
    """gpt-oss-120b trata de forma errática response_mime_type: el JSON se
    exige en la instrucción y RF-38 lo valida."""
    monkeypatch.delenv("VERTEX_INFERENCE_MODEL", raising=False)
    respuesta = MagicMock()
    respuesta.text = '{"ok": true}'
    respuesta.usage_metadata = None
    cliente_sdk = MagicMock()
    cliente_sdk.models.generate_content.return_value = respuesta
    cliente = ClienteInferenciaVertex()
    with patch.object(cliente, "_obtener_cliente", return_value=cliente_sdk):
        resultado = cliente._generar_sincrono("instrucción")
    llamada = cliente_sdk.models.generate_content.call_args.kwargs
    assert "config" not in llamada
    assert llamada["model"] == MODELO_POR_DEFECTO
    assert resultado.texto == '{"ok": true}'
