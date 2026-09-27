import json
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import (EvaluacionFallida,
                                                          EvaluarDiagnostico)
from src.dominio.entidades.evaluacion import (DimensionCalculada,
                                              PerfilCulturalCalculado,
                                              ResultadoCalculo,
                                              SolicitudEvaluacion)


def crear_solicitud_prueba() -> SolicitudEvaluacion:
    return SolicitudEvaluacion(
        diagnostico_id="diag-1",
        empresa_id="emp-1",
        modelo_version="1",
        resultado_calculo=ResultadoCalculo(
            indice_global=Decimal("6.8"),
            nivel=2,
            nivel_nombre="En desarrollo",
            nivel_descripcion="...",
            dimensiones=[DimensionCalculada(codigo="innovacion", puntaje=Decimal("8"))],
            perfil_cultural=PerfilCulturalCalculado(codigo="ENFP"),
        ),
        respuestas=[],
        dimensiones_modelo=[],
        niveles_modelo=[],
    )


def crear_respuesta_agente_valida_json() -> str:
    return json.dumps(
        {
            "perfil_cultura_descripcion": "Descripción",
            "sintesis": "Síntesis",
            "dimensiones_observaciones": {"innovacion": "Observación"},
            "lienzo_negocio": {
                "segmentos_clientes": "...",
                "propuesta_valor": "...",
                "canales": "...",
                "relacion_clientes": "...",
                "fuente_ingresos": "...",
                "recursos_clave": "...",
                "actividades_clave": "...",
                "alianzas_clave": "...",
                "estructura_costos": "...",
            },
            "recomendaciones": [
                {
                    "dimension_codigo": "innovacion",
                    "titulo": "T",
                    "contenido": "C",
                    "prioridad": 1,
                }
            ],
        }
    )


def crear_mocks():
    repo_fragmento = AsyncMock()
    repo_fragmento.buscar_por_similitud.return_value = []
    cliente_embeddings = AsyncMock()
    cliente_embeddings.generar.return_value = [0.1]
    cliente_inferencia = AsyncMock()
    repo_ejecucion = AsyncMock()
    return repo_fragmento, cliente_embeddings, cliente_inferencia, repo_ejecucion


@pytest.mark.asyncio
async def test_evaluar_diagnostico_exitoso_a_la_primera():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.return_value = crear_respuesta_agente_valida_json()
    caso_uso = EvaluarDiagnostico(repo_fragmento, embeddings, inferencia, ejecuciones)

    resultado = await caso_uso.ejecutar(crear_solicitud_prueba())

    assert resultado.sintesis == "Síntesis"
    assert inferencia.generar.call_count == 1
    ejecuciones.registrar.assert_called_once()
    assert ejecuciones.registrar.call_args[0][0].estado == "exitosa"


@pytest.mark.asyncio
async def test_evaluar_diagnostico_reintenta_ante_json_invalido():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = [
        "esto no es json",
        crear_respuesta_agente_valida_json(),
    ]
    caso_uso = EvaluarDiagnostico(repo_fragmento, embeddings, inferencia, ejecuciones)

    resultado = await caso_uso.ejecutar(crear_solicitud_prueba())

    assert resultado.sintesis == "Síntesis"
    assert inferencia.generar.call_count == 2
    assert ejecuciones.registrar.call_count == 2
    estados = [c[0][0].estado for c in ejecuciones.registrar.call_args_list]
    assert estados == ["fallida", "exitosa"]


@pytest.mark.asyncio
async def test_evaluar_diagnostico_agota_intentos_y_falla():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.return_value = "siempre invalido"
    caso_uso = EvaluarDiagnostico(repo_fragmento, embeddings, inferencia, ejecuciones)

    with pytest.raises(EvaluacionFallida):
        await caso_uso.ejecutar(crear_solicitud_prueba())

    assert inferencia.generar.call_count == 3
    assert ejecuciones.registrar.call_count == 3


@pytest.mark.asyncio
async def test_evaluar_diagnostico_reintenta_ante_error_del_proveedor():
    """Encontrado en vivo (429 RESOURCE_EXHAUSTED de Vertex AI): un error
    del propio cliente de inferencia (red, límite de tasa, tiempo de
    espera) no debe propagarse sin más — se trata igual que una respuesta
    inválida y se reintenta."""
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = [
        RuntimeError("429 RESOURCE_EXHAUSTED"),
        crear_respuesta_agente_valida_json(),
    ]
    caso_uso = EvaluarDiagnostico(repo_fragmento, embeddings, inferencia, ejecuciones)

    resultado = await caso_uso.ejecutar(crear_solicitud_prueba())

    assert resultado.sintesis == "Síntesis"
    assert inferencia.generar.call_count == 2
    estados = [c[0][0].estado for c in ejecuciones.registrar.call_args_list]
    assert estados == ["fallida", "exitosa"]


@pytest.mark.asyncio
async def test_evaluar_diagnostico_reintenta_ante_esquema_incompleto():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    respuesta_incompleta = json.dumps({"sintesis": "solo esto"})
    inferencia.generar.side_effect = [
        respuesta_incompleta,
        crear_respuesta_agente_valida_json(),
    ]
    caso_uso = EvaluarDiagnostico(repo_fragmento, embeddings, inferencia, ejecuciones)

    resultado = await caso_uso.ejecutar(crear_solicitud_prueba())

    assert resultado is not None
    assert inferencia.generar.call_count == 2
