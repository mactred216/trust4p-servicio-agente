from unittest.mock import AsyncMock, patch

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import (EvaluacionFallida,
                                                          EvaluarDiagnostico)
from tests.unitarias.aplicacion.test_evaluar_diagnostico import (
    crear_mocks, crear_respuesta_agente_valida_json,
    crear_resultado_inferencia, crear_solicitud_prueba)

RUTA_SLEEP = "src.aplicacion.casos_uso.evaluar_diagnostico.asyncio.sleep"


@pytest.mark.asyncio
async def test_espera_con_crecimiento_exponencial_ante_errores_del_proveedor():
    """ASR-02: un 429 transitorio de Vertex AI no debe agotar los intentos al instante."""
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = [
        RuntimeError("429 RESOURCE_EXHAUSTED"),
        RuntimeError("429 RESOURCE_EXHAUSTED"),
        crear_respuesta_agente_valida_json(),
    ]
    caso_uso = EvaluarDiagnostico(
        repo_fragmento,
        embeddings,
        inferencia,
        ejecuciones,
        espera_reintento_segundos=2.0,
    )

    with patch(RUTA_SLEEP, new_callable=AsyncMock) as dormir:
        resultado = await caso_uso.ejecutar(crear_solicitud_prueba())

    assert resultado.sintesis == "Síntesis"
    assert [c.args[0] for c in dormir.call_args_list] == [2.0, 4.0]


@pytest.mark.asyncio
async def test_no_espera_tras_el_ultimo_intento():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
    caso_uso = EvaluarDiagnostico(
        repo_fragmento,
        embeddings,
        inferencia,
        ejecuciones,
        espera_reintento_segundos=1.0,
    )

    with patch(RUTA_SLEEP, new_callable=AsyncMock) as dormir:
        with pytest.raises(EvaluacionFallida):
            await caso_uso.ejecutar(crear_solicitud_prueba())

    assert dormir.call_count == 2  # tras el intento 1 y el 2, no tras el 3


@pytest.mark.asyncio
async def test_una_respuesta_invalida_se_reintenta_sin_esperar():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = [
        crear_resultado_inferencia("no es json"),
        crear_respuesta_agente_valida_json(),
    ]
    caso_uso = EvaluarDiagnostico(
        repo_fragmento,
        embeddings,
        inferencia,
        ejecuciones,
        espera_reintento_segundos=5.0,
    )

    with patch(RUTA_SLEEP, new_callable=AsyncMock) as dormir:
        await caso_uso.ejecutar(crear_solicitud_prueba())

    dormir.assert_not_called()


@pytest.mark.asyncio
async def test_sin_espera_configurada_no_duerme():
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = [
        RuntimeError("429"),
        crear_respuesta_agente_valida_json(),
    ]
    caso_uso = EvaluarDiagnostico(repo_fragmento, embeddings, inferencia, ejecuciones)

    with patch(RUTA_SLEEP, new_callable=AsyncMock) as dormir:
        await caso_uso.ejecutar(crear_solicitud_prueba())

    dormir.assert_not_called()
