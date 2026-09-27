from src.dominio.entidades.evaluacion import SolicitudEvaluacion
from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento
from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings
from src.dominio.puertos.repositorio_fragmento_conocimiento import \
    RepositorioFragmentoConocimiento
from src.dominio.servicios.validador_esquema import BLOQUES_LIENZO_NEGOCIO

VERSION_PLANTILLA_INSTRUCCIONES = "1.0"

# RF-40: se versiona de forma independiente del código y se registra en
# cada diagnóstico. No existe todavía un Anexo C con el texto definitivo
# (el propio documento de tesis lo deja como pendiente: "TOCA TENIENDO EN
# BASE LAS PREGUNTAS Y EL PESO QUE TIENE CADA UNA DE ELLAS") — esta es una
# primera versión, construida a partir de los cuatro elementos que sí están
# descritos (formato de salida, reglas de negocio, registro comunicativo,
# límites de comportamiento), sujeta a que Mateo la ajuste.
INSTRUCCION_BASE = """Eres un asistente experto en evaluación de madurez de innovación organizacional, apoyando a la consultora Trust 4P.

REGLAS OBLIGATORIAS:
- Usa exclusivamente la información entregada en este mensaje. No infieras datos que la empresa no reportó.
- El índice, el nivel y los puntajes por dimensión del bloque "RESULTADO CALCULADO" ya fueron calculados por el motor determinístico del sistema. Son definitivos y NO MODIFICABLES: tu tarea es interpretarlos y redactarlos en lenguaje natural, nunca recalcularlos ni contradecirlos.
- Ajusta tu interpretación estrictamente a la rúbrica del modelo de madurez entregada en "CONFIGURACIÓN DEL MODELO", no a un criterio propio.
- Justifica cada valoración que hagas dentro del campo correspondiente.
- Si la información entregada es insuficiente para alguna parte de tu respuesta, decláralo explícitamente en esa parte en vez de inventar contenido.

REGISTRO COMUNICATIVO: escribe en un lenguaje comprensible para perfiles directivos sin formación técnica.

LÍMITES DE COMPORTAMIENTO:
- No emitas juicios sobre las personas de la organización.
- No compares con empresas identificables.
- Presenta tu resultado como un insumo para la decisión del consultor, no como un veredicto.

FORMATO DE SALIDA: responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes ni después, con exactamente esta forma (sustituye cada "..." por tu contenido):
{
  "perfil_cultura_descripcion": "...",
  "dimensiones_observaciones": {"<codigo_de_cada_dimension_de_CONFIGURACION_DEL_MODELO>": "..."},
  "lienzo_negocio": {"segmentos_clientes": "...", "propuesta_valor": "...", "canales": "...", "relacion_clientes": "...", "fuente_ingresos": "...", "recursos_clave": "...", "actividades_clave": "...", "alianzas_clave": "...", "estructura_costos": "..."},
  "sintesis": "...",
  "recomendaciones": [{"dimension_codigo": "...", "titulo": "...", "contenido": "...", "prioridad": 1}]
}
"""

LIMITE_FRAGMENTOS_POR_CATEGORIA = 2


async def recuperar_contexto(
    solicitud: SolicitudEvaluacion,
    repo_fragmento: RepositorioFragmentoConocimiento,
    cliente_embeddings: ClienteEmbeddings,
) -> list[FragmentoConocimiento]:
    """RF-36/Tabla 17: recupera, por similitud, el material de la base de
    conocimiento — perfiles de cultura relevantes al código determinado,
    criterios de valoración priorizando las dimensiones de menor puntaje, y
    ejemplos de diagnósticos calificados con un perfil similar."""
    fragmentos: list[FragmentoConocimiento] = []
    vistos: set[str] = set()

    def _agregar(nuevos: list[FragmentoConocimiento]) -> None:
        for f in nuevos:
            if f.id not in vistos:
                vistos.add(f.id)
                fragmentos.append(f)

    perfil = solicitud.resultado_calculo.perfil_cultural
    consulta_perfil = f"Perfil cultural de innovación con código {perfil.codigo}"
    embedding_perfil = await cliente_embeddings.generar(consulta_perfil)
    _agregar(
        await repo_fragmento.buscar_por_similitud(
            embedding_perfil,
            categoria="perfiles_cultura",
            limite=LIMITE_FRAGMENTOS_POR_CATEGORIA,
        )
    )

    dimensiones_ordenadas = sorted(
        solicitud.resultado_calculo.dimensiones, key=lambda d: d.puntaje
    )
    if dimensiones_ordenadas:
        peor_dimension = dimensiones_ordenadas[0]
        consulta_rubrica = (
            f"Criterios de valoración para la dimensión {peor_dimension.codigo} "
            f"con puntaje bajo ({peor_dimension.puntaje})"
        )
        embedding_rubrica = await cliente_embeddings.generar(consulta_rubrica)
        _agregar(
            await repo_fragmento.buscar_por_similitud(
                embedding_rubrica,
                categoria="rubrica",
                limite=LIMITE_FRAGMENTOS_POR_CATEGORIA,
            )
        )

    consulta_ejemplos = (
        f"Diagnóstico de nivel {solicitud.resultado_calculo.nivel} "
        f"({solicitud.resultado_calculo.nivel_nombre}) con perfil cultural "
        f"{perfil.codigo}"
    )
    embedding_ejemplos = await cliente_embeddings.generar(consulta_ejemplos)
    _agregar(
        await repo_fragmento.buscar_por_similitud(
            embedding_ejemplos,
            categoria="ejemplos",
            limite=LIMITE_FRAGMENTOS_POR_CATEGORIA,
        )
    )

    return fragmentos


def componer_instruccion(
    solicitud: SolicitudEvaluacion, fragmentos: list[FragmentoConocimiento]
) -> str:
    """RF-36/Tabla 13: arma los tres bloques, de lo general a lo particular
    (configuración antes que el caso a evaluar), precedidos por la
    instrucción base."""
    resultado = solicitud.resultado_calculo

    bloque_configuracion = ["CONFIGURACIÓN DEL MODELO (no modificable):"]
    for d in sorted(solicitud.dimensiones_modelo, key=lambda d: d.orden):
        bloque_configuracion.append(
            f"- Dimensión {d.codigo} ({d.nombre}): peso {d.peso}"
        )
    for n in sorted(solicitud.niveles_modelo, key=lambda n: n.nivel):
        bloque_configuracion.append(
            f"- Nivel {n.nivel} ({n.nombre}): {n.umbral_min} a {n.umbral_max} — {n.descripcion}"
        )

    bloque_diagnostico = ["RESULTADO CALCULADO (no modificable):"]
    bloque_diagnostico.append(
        f"- Índice global: {resultado.indice_global}, Nivel {resultado.nivel} "
        f"({resultado.nivel_nombre}): {resultado.nivel_descripcion}"
    )
    for d in resultado.dimensiones:
        bloque_diagnostico.append(f"- Dimensión {d.codigo}: puntaje {d.puntaje}")
    bloque_diagnostico.append(
        f"- Código de perfil cultural: {resultado.perfil_cultural.codigo}"
    )
    bloque_diagnostico.append("RESPUESTAS DEL DIAGNÓSTICO:")
    for r in solicitud.respuestas:
        valor = (
            ", ".join(r.opciones_codigo)
            if r.opciones_codigo
            else (str(r.valor) if r.valor is not None else (r.texto or ""))
        )
        bloque_diagnostico.append(f"- [{r.dimension_codigo}] {r.enunciado} -> {valor}")

    bloque_conocimiento = ["MATERIAL DE REFERENCIA RECUPERADO:"]
    if not fragmentos:
        bloque_conocimiento.append("(sin fragmentos recuperados)")
    for f in fragmentos:
        bloque_conocimiento.append(f"- [{f.categoria}] {f.contenido}")

    return "\n\n".join(
        [
            INSTRUCCION_BASE,
            "\n".join(bloque_configuracion),
            "\n".join(bloque_diagnostico),
            "\n".join(bloque_conocimiento),
        ]
    )


def construir_peticion_auditoria(
    solicitud: SolicitudEvaluacion, fragmentos: list[FragmentoConocimiento]
) -> dict:
    """R-13: guarda el contenido efectivamente enviado, con cada fragmento
    truncado a un extracto — el contenido íntegro se recupera por el id en
    fragmentos_recuperados, no se duplica aquí."""
    return {
        "empresa_id": solicitud.empresa_id,
        "modelo_version": solicitud.modelo_version,
        "resultado_calculo": {
            "indice_global": str(solicitud.resultado_calculo.indice_global),
            "nivel": solicitud.resultado_calculo.nivel,
            "perfil_cultural_codigo": solicitud.resultado_calculo.perfil_cultural.codigo,
        },
        "respuestas_count": len(solicitud.respuestas),
        "fragmentos_extracto": [
            {"categoria": f.categoria, "extracto": f.contenido[:120]}
            for f in fragmentos
        ],
    }
