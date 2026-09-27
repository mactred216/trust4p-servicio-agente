from typing import Any

from src.dominio.entidades.evaluacion import (RecomendacionAgente,
                                              RespuestaAgente)

# RF-15: los nueve bloques del lienzo de modelo de negocio de Osterwalder y
# Pigneur (2010).
BLOQUES_LIENZO_NEGOCIO = {
    "segmentos_clientes",
    "propuesta_valor",
    "canales",
    "relacion_clientes",
    "fuente_ingresos",
    "recursos_clave",
    "actividades_clave",
    "alianzas_clave",
    "estructura_costos",
}


class RespuestaAgenteInvalida(Exception):
    """RF-38: la respuesta del agente no cumple el esquema esperado."""


def _validar_texto_no_vacio(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise RespuestaAgenteInvalida(f"'{campo}' debe ser texto no vacío")
    return valor


def validar_respuesta_agente(
    datos: dict, codigos_dimensiones_esperados: set[str]
) -> RespuestaAgente:
    """RF-38: valida campos requeridos y tipos antes de aceptar la respuesta.
    No valida ningún campo numérico porque el esquema no los declara — eso
    ya está resuelto por el motor de cálculo (RF-37/Tabla 19)."""
    if not isinstance(datos, dict):
        raise RespuestaAgenteInvalida("La respuesta del agente no es un objeto JSON")

    perfil_cultura_descripcion = _validar_texto_no_vacio(
        datos.get("perfil_cultura_descripcion"), "perfil_cultura_descripcion"
    )
    sintesis = _validar_texto_no_vacio(datos.get("sintesis"), "sintesis")

    dimensiones_observaciones = datos.get("dimensiones_observaciones")
    if not isinstance(dimensiones_observaciones, dict):
        raise RespuestaAgenteInvalida("'dimensiones_observaciones' debe ser un objeto")
    faltantes = codigos_dimensiones_esperados - set(dimensiones_observaciones.keys())
    if faltantes:
        raise RespuestaAgenteInvalida(
            f"Faltan observaciones para las dimensiones: {sorted(faltantes)}"
        )
    for codigo, observacion in dimensiones_observaciones.items():
        _validar_texto_no_vacio(observacion, f"dimensiones_observaciones.{codigo}")

    lienzo_negocio = datos.get("lienzo_negocio")
    if not isinstance(lienzo_negocio, dict):
        raise RespuestaAgenteInvalida("'lienzo_negocio' debe ser un objeto")
    bloques_faltantes = BLOQUES_LIENZO_NEGOCIO - set(lienzo_negocio.keys())
    if bloques_faltantes:
        raise RespuestaAgenteInvalida(
            f"Faltan bloques del lienzo de negocio: {sorted(bloques_faltantes)}"
        )
    for bloque, contenido in lienzo_negocio.items():
        _validar_texto_no_vacio(contenido, f"lienzo_negocio.{bloque}")

    recomendaciones_datos = datos.get("recomendaciones")
    if not isinstance(recomendaciones_datos, list) or not recomendaciones_datos:
        raise RespuestaAgenteInvalida(
            "'recomendaciones' debe ser una lista con al menos un elemento"
        )
    recomendaciones = []
    for i, r in enumerate(recomendaciones_datos):
        if not isinstance(r, dict):
            raise RespuestaAgenteInvalida(f"recomendaciones[{i}] debe ser un objeto")
        dimension_codigo = _validar_texto_no_vacio(
            r.get("dimension_codigo"), f"recomendaciones[{i}].dimension_codigo"
        )
        titulo = _validar_texto_no_vacio(
            r.get("titulo"), f"recomendaciones[{i}].titulo"
        )
        contenido = _validar_texto_no_vacio(
            r.get("contenido"), f"recomendaciones[{i}].contenido"
        )
        prioridad = r.get("prioridad")
        if (
            not isinstance(prioridad, int)
            or isinstance(prioridad, bool)
            or prioridad < 1
        ):
            raise RespuestaAgenteInvalida(
                f"recomendaciones[{i}].prioridad debe ser un entero positivo"
            )
        recomendaciones.append(
            RecomendacionAgente(
                dimension_codigo=dimension_codigo,
                titulo=titulo,
                contenido=contenido,
                prioridad=prioridad,
            )
        )

    return RespuestaAgente(
        perfil_cultura_descripcion=perfil_cultura_descripcion,
        dimensiones_observaciones=dimensiones_observaciones,
        lienzo_negocio=lienzo_negocio,
        sintesis=sintesis,
        recomendaciones=recomendaciones,
    )
