from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.compositor_contexto import (componer_instruccion,
                                                construir_peticion_auditoria,
                                                recuperar_contexto)
from src.dominio.entidades.evaluacion import (DimensionCalculada,
                                              DimensionModelo, NivelModelo,
                                              PerfilCulturalCalculado,
                                              ResultadoCalculo,
                                              SolicitudEvaluacion)
from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento


def crear_solicitud_prueba() -> SolicitudEvaluacion:
    return SolicitudEvaluacion(
        diagnostico_id="diag-1",
        empresa_id="emp-1",
        modelo_version="1",
        resultado_calculo=ResultadoCalculo(
            indice_global=Decimal("6.8"),
            nivel=2,
            nivel_nombre="En desarrollo",
            nivel_descripcion="Nivel medio",
            dimensiones=[
                DimensionCalculada(codigo="innovacion", puntaje=Decimal("8")),
                DimensionCalculada(codigo="procesos", puntaje=Decimal("5")),
            ],
            perfil_cultural=PerfilCulturalCalculado(codigo="ENFP"),
        ),
        respuestas=[],
        dimensiones_modelo=[
            DimensionModelo(
                codigo="innovacion", nombre="Innovación", peso=Decimal("0.6"), orden=1
            ),
            DimensionModelo(
                codigo="procesos", nombre="Procesos", peso=Decimal("0.4"), orden=2
            ),
        ],
        niveles_modelo=[
            NivelModelo(
                nivel=2,
                nombre="En desarrollo",
                descripcion="...",
                umbral_min=Decimal("4"),
                umbral_max=Decimal("7"),
            ),
        ],
    )


def crear_fragmento(
    id="f1", categoria="perfiles_cultura", contenido="texto de referencia"
) -> FragmentoConocimiento:
    return FragmentoConocimiento(
        id=id,
        documento_id="doc-1",
        categoria=categoria,
        orden=1,
        contenido=contenido,
        embedding=[0.1, 0.2],
    )


@pytest.mark.asyncio
async def test_recuperar_contexto_llama_al_repositorio_por_categoria():
    solicitud = crear_solicitud_prueba()
    repo_fragmento = AsyncMock()
    repo_fragmento.buscar_por_similitud.return_value = [crear_fragmento()]
    cliente_embeddings = AsyncMock()
    cliente_embeddings.generar.return_value = [0.1, 0.2]

    fragmentos = await recuperar_contexto(solicitud, repo_fragmento, cliente_embeddings)

    categorias_consultadas = [
        c.kwargs["categoria"]
        for c in repo_fragmento.buscar_por_similitud.call_args_list
    ]
    assert categorias_consultadas == [
        "perfiles_cultura",
        "rubrica",
        "ejemplos",
        "dimensiones",
        "marco_teorico",
    ]
    assert len(fragmentos) > 0


@pytest.mark.asyncio
async def test_recuperar_contexto_prioriza_dimension_de_menor_puntaje():
    solicitud = crear_solicitud_prueba()
    repo_fragmento = AsyncMock()
    repo_fragmento.buscar_por_similitud.return_value = []
    cliente_embeddings = AsyncMock()
    cliente_embeddings.generar.return_value = [0.1]

    await recuperar_contexto(solicitud, repo_fragmento, cliente_embeddings)

    consultas = [c.args[0] for c in cliente_embeddings.generar.call_args_list]
    consulta_rubrica = next(c for c in consultas if "procesos" in c.lower())
    assert "procesos" in consulta_rubrica  # procesos tiene el puntaje mas bajo (5 < 8)


@pytest.mark.asyncio
async def test_recuperar_contexto_no_duplica_fragmentos_repetidos():
    solicitud = crear_solicitud_prueba()
    repo_fragmento = AsyncMock()
    repo_fragmento.buscar_por_similitud.return_value = [crear_fragmento(id="f1")]
    cliente_embeddings = AsyncMock()
    cliente_embeddings.generar.return_value = [0.1]

    fragmentos = await recuperar_contexto(solicitud, repo_fragmento, cliente_embeddings)

    assert len(fragmentos) == 1


def test_componer_instruccion_incluye_los_tres_bloques():
    solicitud = crear_solicitud_prueba()
    fragmentos = [crear_fragmento()]

    instruccion = componer_instruccion(solicitud, fragmentos)

    assert "CONFIGURACIÓN DEL MODELO" in instruccion
    assert "RESULTADO CALCULADO" in instruccion
    assert "MATERIAL DE REFERENCIA" in instruccion
    assert "ENFP" in instruccion
    assert "no modificable" in instruccion.lower()


def test_componer_instruccion_pide_formato_json():
    instruccion = componer_instruccion(crear_solicitud_prueba(), [])
    assert "JSON" in instruccion
    assert "dimensiones_observaciones" in instruccion
    assert "lienzo_negocio" in instruccion


def test_construir_peticion_auditoria_trunca_fragmentos():
    """R-13: el extracto se guarda truncado, no el contenido íntegro."""
    contenido_largo = "x" * 500
    fragmentos = [crear_fragmento(contenido=contenido_largo)]

    peticion = construir_peticion_auditoria(crear_solicitud_prueba(), fragmentos)

    assert len(peticion["fragmentos_extracto"][0]["extracto"]) <= 120
    assert "empresa_id" in peticion


@pytest.mark.asyncio
async def test_la_consulta_de_dimensiones_usa_los_nombres_vigentes_del_modelo():
    solicitud = crear_solicitud_prueba()
    repo_fragmento = AsyncMock()
    repo_fragmento.buscar_por_similitud.return_value = []
    cliente_embeddings = AsyncMock()
    cliente_embeddings.generar.return_value = [0.1]

    await recuperar_contexto(solicitud, repo_fragmento, cliente_embeddings)

    consultas = [c.args[0] for c in cliente_embeddings.generar.call_args_list]
    consulta = next(
        c for c in consultas if c.startswith("Descripción de las dimensiones")
    )
    for dimension in solicitud.dimensiones_modelo:
        assert dimension.nombre in consulta
