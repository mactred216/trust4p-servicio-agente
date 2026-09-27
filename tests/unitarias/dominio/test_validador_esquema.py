import pytest

from src.dominio.servicios.validador_esquema import (RespuestaAgenteInvalida,
                                                     validar_respuesta_agente)


def crear_lienzo_completo() -> dict:
    return {
        "segmentos_clientes": "...",
        "propuesta_valor": "...",
        "canales": "...",
        "relacion_clientes": "...",
        "fuente_ingresos": "...",
        "recursos_clave": "...",
        "actividades_clave": "...",
        "alianzas_clave": "...",
        "estructura_costos": "...",
    }


def crear_respuesta_valida() -> dict:
    return {
        "perfil_cultura_descripcion": "Descripción del perfil",
        "sintesis": "Síntesis general",
        "dimensiones_observaciones": {"innovacion": "Observación", "procesos": "Obs"},
        "lienzo_negocio": crear_lienzo_completo(),
        "recomendaciones": [
            {
                "dimension_codigo": "innovacion",
                "titulo": "Título",
                "contenido": "Contenido",
                "prioridad": 1,
            }
        ],
    }


def test_respuesta_valida_se_acepta():
    resultado = validar_respuesta_agente(
        crear_respuesta_valida(), {"innovacion", "procesos"}
    )
    assert resultado.sintesis == "Síntesis general"
    assert len(resultado.recomendaciones) == 1


def test_no_es_un_objeto_falla():
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente("no soy un json", {"innovacion"})


def test_falta_sintesis_falla():
    datos = crear_respuesta_valida()
    del datos["sintesis"]
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente(datos, {"innovacion", "procesos"})


def test_falta_observacion_de_una_dimension_falla():
    datos = crear_respuesta_valida()
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente(datos, {"innovacion", "procesos", "cultura"})


def test_falta_bloque_del_lienzo_falla():
    datos = crear_respuesta_valida()
    del datos["lienzo_negocio"]["propuesta_valor"]
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente(datos, {"innovacion", "procesos"})


def test_recomendaciones_vacias_falla():
    datos = crear_respuesta_valida()
    datos["recomendaciones"] = []
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente(datos, {"innovacion", "procesos"})


def test_prioridad_no_entera_falla():
    datos = crear_respuesta_valida()
    datos["recomendaciones"][0]["prioridad"] = "alta"
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente(datos, {"innovacion", "procesos"})


def test_prioridad_booleana_falla():
    """bool es subclase de int en Python; debe rechazarse explícitamente."""
    datos = crear_respuesta_valida()
    datos["recomendaciones"][0]["prioridad"] = True
    with pytest.raises(RespuestaAgenteInvalida):
        validar_respuesta_agente(datos, {"innovacion", "procesos"})
