from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.consultar_ejecuciones_agente import \
    ConsultarEjecucionesAgente
from src.dominio.entidades.ejecucion_agente import EjecucionAgente


@pytest.mark.asyncio
async def test_ejecutar_devuelve_las_ejecuciones_del_diagnostico():
    repo_ejecucion = AsyncMock()
    repo_ejecucion.listar_por_diagnostico.return_value = [
        EjecucionAgente(
            id="e1",
            diagnostico_id="diag-1",
            intento=1,
            peticion={"empresa_id": "emp-1"},
            fragmentos_recuperados=[],
            proveedor="google-vertex-ai",
            modelo="qwen3-next-80b-a3b-instruct-maas",
            version_prompt="1.0",
            modelo_version="1",
            estado="exitosa",
            respuesta={"sintesis": "..."},
        )
    ]
    caso_uso = ConsultarEjecucionesAgente(repo_ejecucion)

    ejecuciones = await caso_uso.ejecutar("diag-1")

    assert len(ejecuciones) == 1
    repo_ejecucion.listar_por_diagnostico.assert_called_once_with("diag-1")


@pytest.mark.asyncio
async def test_ejecutar_sin_ejecuciones_devuelve_lista_vacia():
    repo_ejecucion = AsyncMock()
    repo_ejecucion.listar_por_diagnostico.return_value = []
    caso_uso = ConsultarEjecucionesAgente(repo_ejecucion)

    assert await caso_uso.ejecutar("diag-sin-ejecuciones") == []
