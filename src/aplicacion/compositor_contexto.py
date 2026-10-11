from src.dominio.entidades.evaluacion import SolicitudEvaluacion
from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento
from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings
from src.dominio.puertos.repositorio_fragmento_conocimiento import \
    RepositorioFragmentoConocimiento
from src.dominio.servicios.validador_esquema import BLOQUES_LIENZO_NEGOCIO

VERSION_PLANTILLA_INSTRUCCIONES = "2.0"

# RF-40: se versiona de forma independiente del código y se registra en
# cada diagnóstico, de modo que una evaluación pueda atribuirse a la versión
# de plantilla con que se produjo.
#
# Versión 2.0: la 1.0 no declaraba extensión ni estructura para ningún campo,
# y el modelo resolvía cada recomendación en una sola frase —correcta, pero
# sin pasos, sin responsable y sin forma de verificar si se cumplió—. Esta
# versión conserva intactas las reglas de negocio, el registro comunicativo y
# los límites de comportamiento, y añade lo que faltaba: qué debe contener
# cada campo, con qué extensión y en qué orden.
INSTRUCCION_BASE = """Eres un asistente experto en evaluación de madurez de innovación organizacional, apoyando a la consultora Trust 4P. Tu salida la lee un consultor que la usará para conversar con la empresa, de modo que debe ser accionable, no una descripción del puntaje.

REGLAS OBLIGATORIAS:
- Usa exclusivamente la información entregada en este mensaje. No infieras datos que la empresa no reportó.
- El índice, el nivel y los puntajes por dimensión del bloque "RESULTADO CALCULADO" ya fueron calculados por el motor determinístico del sistema. Son definitivos y NO MODIFICABLES: tu tarea es interpretarlos y redactarlos en lenguaje natural, nunca recalcularlos ni contradecirlos.
- Ajusta tu interpretación estrictamente a la rúbrica del modelo de madurez entregada en "CONFIGURACIÓN DEL MODELO", no a un criterio propio.
- Justifica cada valoración que hagas dentro del campo correspondiente, citando la respuesta del diagnóstico que la sustenta y su nivel.
- Si la información entregada es insuficiente para alguna parte de tu respuesta, decláralo explícitamente en esa parte, di qué información haría falta, y no inventes contenido.
- Cuando el MATERIAL DE REFERENCIA RECUPERADO contradiga la configuración del modelo o la metodología propia de Trust 4P, prevalece esta última.
- Escribe todo en español, incluidos los rótulos internos de cada recomendación.

REGISTRO COMUNICATIVO: escribe en un lenguaje comprensible para perfiles directivos sin formación técnica.

LÍMITES DE COMPORTAMIENTO:
- No emitas juicios sobre las personas de la organización.
- No compares con empresas identificables.
- Presenta tu resultado como un insumo para la decisión del consultor, no como un veredicto.

EXTENSIÓN Y ESTRUCTURA DE CADA CAMPO:

"dimensiones_observaciones": una entrada por dimensión, de 120 a 180 palabras, en tres párrafos separados por una línea en blanco.
  Párrafo 1: qué hace hoy la organización en esa dimensión, citando las respuestas que lo sustentan con su nivel.
  Párrafo 2: qué le falta, y por qué eso explica el puntaje obtenido.
  Párrafo 3: qué riesgo o costo concreto acarrea esa brecha si no se cierra.

"recomendaciones": de una a dos por dimensión. Dos para las dimensiones de menor puntaje; una para las demás. Ordena el arreglo de mayor a menor urgencia y numera "prioridad" de forma consecutiva desde 1, sin repetir ni saltar.
  "titulo": una acción concreta en una línea, sin punto final.
  "contenido": de 150 a 250 palabras, con estos seis bloques en este orden, cada uno iniciado por su rótulo seguido de dos puntos y separado del siguiente por una línea en blanco. Texto corrido, sin viñetas, sin guiones de lista y sin marcado:
    Qué hacer: la acción, en dos o tres oraciones, partiendo de la brecha observada.
    Primeros pasos: tres acciones concretas y ordenadas que puedan empezarse en las próximas semanas, enumeradas dentro del mismo párrafo.
    Quién debe liderarlo: el rol responsable, nunca un nombre propio.
    Evidencia de cumplimiento: qué documento, registro o indicador debería existir cuando la recomendación esté cumplida.
    Horizonte: corto, medio o largo plazo, con el número estimado de meses.
    Efecto esperado: qué pregunta del diagnóstico debería subir de nivel y qué significa eso para la dimensión. No prometas un valor de índice ni de puntaje.

"sintesis": de 150 a 220 palabras, en tres párrafos separados por una línea en blanco: la lectura general del estado de madurez; la tensión principal que revela el diagnóstico, es decir qué contrasta con qué; y por dónde empezar y por qué ese orden y no otro.

"perfil_cultura_descripcion": de 80 a 120 palabras. Qué caracteriza a ese perfil y cómo se manifiesta en las respuestas de esta organización en particular.

"lienzo_negocio": un bloque por cada una de las nueve claves. Si las respuestas del diagnóstico no aportan información sobre un bloque, dilo de forma explícita y señala qué haría falta preguntar. No deduzcas el modelo de negocio de la empresa a partir de su madurez de innovación.

FORMATO DE SALIDA: responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes ni después, con exactamente esta forma (sustituye cada "..." por tu contenido). Los saltos de línea dentro de un texto van escapados como \\n, según exige JSON:
{
  "perfil_cultura_descripcion": "...",
  "dimensiones_observaciones": {"<codigo_de_cada_dimension_de_CONFIGURACION_DEL_MODELO>": "..."},
  "lienzo_negocio": {"segmentos_clientes": "...", "propuesta_valor": "...", "canales": "...", "relacion_clientes": "...", "fuente_ingresos": "...", "recursos_clave": "...", "actividades_clave": "...", "alianzas_clave": "...", "estructura_costos": "..."},
  "sintesis": "...",
  "recomendaciones": [{"dimension_codigo": "...", "titulo": "...", "contenido": "...", "prioridad": 1}]
}
"""

# Por categoría, no en total: con las cinco categorías pobladas se recuperan
# hasta veinte fragmentos. Estaba en 2 y con una base de conocimiento pequeña
# bastaba; al crecer el material, dos fragmentos por categoría dejan fuera casi
# todo lo cargado.
LIMITE_FRAGMENTOS_POR_CATEGORIA = 4


async def recuperar_contexto(
    solicitud: SolicitudEvaluacion,
    repo_fragmento: RepositorioFragmentoConocimiento,
    cliente_embeddings: ClienteEmbeddings,
) -> list[FragmentoConocimiento]:
    """RF-36/Tabla 17: recupera, por similitud, el material de la base de
    conocimiento — perfiles de cultura relevantes al código determinado,
    criterios de valoración priorizando las dimensiones de menor puntaje,
    ejemplos de diagnósticos calificados con un perfil similar, descripciones
    de las dimensiones y marco teórico."""
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

    # RF-41: las cinco categorias de la base de conocimiento participan. Las
    # descripciones de las dimensiones se buscan con los nombres vigentes del
    # modelo (el administrador puede agregarlas o renombrarlas) y el marco
    # teorico da el contexto conceptual general.
    nombres_dimensiones = ", ".join(
        d.nombre for d in sorted(solicitud.dimensiones_modelo, key=lambda d: d.orden)
    )
    consulta_dimensiones = (
        f"Descripción de las dimensiones del modelo de madurez: {nombres_dimensiones}"
    )
    embedding_dimensiones = await cliente_embeddings.generar(consulta_dimensiones)
    _agregar(
        await repo_fragmento.buscar_por_similitud(
            embedding_dimensiones,
            categoria="dimensiones",
            limite=LIMITE_FRAGMENTOS_POR_CATEGORIA,
        )
    )

    consulta_marco = (
        "Marco teórico de la madurez de innovación y la cultura organizacional"
    )
    embedding_marco = await cliente_embeddings.generar(consulta_marco)
    _agregar(
        await repo_fragmento.buscar_por_similitud(
            embedding_marco,
            categoria="marco_teorico",
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
