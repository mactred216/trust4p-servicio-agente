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
    """ASR-02: un 429 transitorio de Vertex AI no debe agotar los intentos al
    instante. Al tratarse de un límite de tasa, la espera parte del cuádruple
    de la base configurada y se duplica en cada intento."""
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
    assert [c.args[0] for c in dormir.call_args_list] == [8.0, 16.0]


@pytest.mark.asyncio
async def test_no_espera_tras_el_ultimo_intento():
    """Un límite de tasa concede cinco intentos, de modo que hay cuatro
    esperas y ninguna después del último."""
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

    assert dormir.call_count == 4  # tras los intentos 1 a 4, no tras el 5


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


@pytest.mark.asyncio
async def test_un_error_que_no_es_limite_de_tasa_conserva_los_tres_intentos():
    """Solo el 429 amplía el presupuesto de intentos: un fallo de red se
    reintenta tres veces y con la espera base, sin prolongar el diagnóstico."""
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = RuntimeError("Connection reset by peer")
    caso_uso = EvaluarDiagnostico(
        repo_fragmento,
        embeddings,
        inferencia,
        ejecuciones,
        espera_reintento_segundos=2.0,
    )

    with patch(RUTA_SLEEP, new_callable=AsyncMock) as dormir:
        with pytest.raises(EvaluacionFallida):
            await caso_uso.ejecutar(crear_solicitud_prueba())

    assert inferencia.generar.call_count == 3
    assert [c.args[0] for c in dormir.call_args_list] == [2.0, 4.0]


@pytest.mark.asyncio
async def test_un_limite_de_tasa_concede_cinco_intentos():
    """Cuatro 429 seguidos de una respuesta válida terminan en informe, no en
    diagnóstico fallido."""
    repo_fragmento, embeddings, inferencia, ejecuciones = crear_mocks()
    inferencia.generar.side_effect = [
        RuntimeError("429 RESOURCE_EXHAUSTED"),
        RuntimeError("429 RESOURCE_EXHAUSTED"),
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
    assert inferencia.generar.call_count == 5
    assert [c.args[0] for c in dormir.call_args_list] == [8.0, 16.0, 32.0, 64.0]
