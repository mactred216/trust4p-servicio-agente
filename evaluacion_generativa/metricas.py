"""C9: métricas automáticas del componente generativo sobre un caso.

Complementan el juicio experto (plantilla_juicio_experto.csv); no lo
sustituyen. Cada métrica es verificable a partir de la petición, la
respuesta y, si se tiene, la lista de fragmentos recuperados.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from src.dominio.servicios.validador_esquema import validar_respuesta_agente

ROTULOS_RECOMENDACION = ["Qué hacer", "Primeros pasos", "Quién debe liderarlo",
                         "Evidencia de cumplimiento", "Horizonte", "Efecto esperado"]
INDICIOS_INSUFICIENCIA = [
    "no aporta", "no aportan", "no hay informacion", "no se cuenta con", "no se dispone", "insuficiente",
    "haria falta", "hace falta", "falta informacion", "sin informacion", "no permite", "no permiten",
    "no se reporta", "no reporta", "no se menciona", "no menciona", "no incluye", "no incluyen", "seria necesario preguntar",
    "habria que preguntar", "no es posible determinar", "no se puede determinar", "no ofrece", "no ofrecen",
]
PALABRAS_VACIAS = set("""a al algo con cual cuales de del el en es esta este la las lo los mas o para por que se sin su sus un una y
como cuando donde hay hoy tiene tienen ser son fue sobre entre desde hasta qué cómo""".split())
CATEGORIAS_BASE_CONOCIMIENTO = {"perfiles_cultura", "rubrica", "ejemplos", "dimensiones", "marco_teorico"}


def _normal(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _textos(respuesta: dict) -> list[str]:
    salida = [respuesta.get("perfil_cultura_descripcion", ""), respuesta.get("sintesis", "")]
    salida += list((respuesta.get("dimensiones_observaciones") or {}).values())
    salida += list((respuesta.get("lienzo_negocio") or {}).values())
    for r in respuesta.get("recomendaciones") or []:
        salida += [r.get("titulo", ""), r.get("contenido", "")]
    return [t for t in salida if isinstance(t, str)]


def esquema_valido(peticion: dict, respuesta: dict) -> dict:
    codigos = {d["codigo"] for d in peticion["dimensiones_modelo"]}
    try:
        validar_respuesta_agente(respuesta, codigos)
        return {"valido": True, "error": None}
    except Exception as e:  # RespuestaAgenteInvalida u otro error de forma
        return {"valido": False, "error": str(e)}


def _numeros_permitidos(peticion: dict) -> set[Decimal]:
    rc = peticion["resultado_calculo"]
    valores = {Decimal(str(rc["indice_global"])), Decimal(rc["nivel"])}
    valores |= {Decimal(str(d["puntaje"])) for d in rc["dimensiones"]}
    for n in peticion["niveles_modelo"]:
        valores |= {Decimal(n["nivel"]), Decimal(str(n["umbral_min"])), Decimal(str(n["umbral_max"]))}
    return {v.normalize() for v in valores}


_RE_NUMERO_CERCA = re.compile(
    r"\b(indice(?: global)?|puntaje|nivel)\b[^.\d\n]{0,25}?(\d+(?:[.,]\d+)?)", re.I)


def fidelidad_numerica(peticion: dict, respuesta: dict) -> dict:
    """Cifras atribuidas al índice, a un puntaje o a un nivel que no coinciden
    con lo calculado (contradicción del resultado determinístico)."""
    permitidos = _numeros_permitidos(peticion)
    hallados, contradicciones = 0, []
    for texto in _textos(respuesta):
        for m in _RE_NUMERO_CERCA.finditer(_normal(texto)):
            try:
                valor = Decimal(m.group(2).replace(",", ".")).normalize()
            except InvalidOperation:
                continue
            hallados += 1
            redondeos = {valor} | {p for p in permitidos if abs(p - valor) < Decimal("0.6")}
            if not (redondeos & permitidos):
                contradicciones.append(m.group(0))
    return {"cifras_revisadas": hallados, "contradicciones": contradicciones}


def anclaje_observaciones(peticion: dict, respuesta: dict) -> dict:
    """Por dimensión: la observación cita al menos una respuesta de esa
    dimensión (código de pregunta, opción N1-N4 o la mitad de las palabras
    con contenido de un enunciado)."""
    observaciones = respuesta.get("dimensiones_observaciones") or {}
    por_dimension = {}
    for d in peticion["dimensiones_modelo"]:
        texto = _normal(observaciones.get(d["codigo"], ""))
        palabras_texto = set(re.findall(r"\w+", texto))
        anclada = False
        for r in peticion["respuestas"]:
            if r["dimension_codigo"] != d["codigo"]:
                continue
            if _normal(r["pregunta_codigo"]) in texto or any(_normal(o) in palabras_texto for o in r.get("opciones_codigo") or []):
                anclada = True
                break
            claves = {w for w in re.findall(r"\w+", _normal(r["enunciado"])) if w not in PALABRAS_VACIAS and len(w) > 3}
            if claves and len(claves & palabras_texto) / len(claves) >= 0.5:
                anclada = True
                break
        por_dimension[d["codigo"]] = anclada
    total = len(por_dimension) or 1
    return {"proporcion": round(sum(por_dimension.values()) / total, 3), "por_dimension": por_dimension}


def _declara_insuficiencia(texto: str) -> bool:
    t = _normal(texto)
    return any(i in t for i in INDICIOS_INSUFICIENCIA)


def manejo_insuficiencia(esperado: dict, respuesta: dict) -> dict:
    lienzo = respuesta.get("lienzo_negocio") or {}
    sin_info = esperado.get("bloques_sin_informacion", [])
    con_info = esperado.get("bloques_con_informacion", [])
    declarados = [b for b in sin_info if _declara_insuficiencia(lienzo.get(b, ""))]
    inventados = [b for b in sin_info if b not in declarados]
    desaprovechados = [b for b in con_info if _declara_insuficiencia(lienzo.get(b, ""))]
    return {
        "bloques_sin_informacion": len(sin_info),
        "declarados_insuficientes": len(declarados),
        "proporcion": round(len(declarados) / len(sin_info), 3) if sin_info else None,
        "bloques_posiblemente_inventados": inventados,
        "bloques_con_informacion_declarados_insuficientes": desaprovechados,
    }


def recomendaciones(peticion: dict, esperado: dict, respuesta: dict) -> dict:
    recs = respuesta.get("recomendaciones") or []
    codigos = {d["codigo"] for d in peticion["dimensiones_modelo"]}
    prioridades = [r.get("prioridad") for r in recs]
    con_rotulos = sum(all(rot in (r.get("contenido") or "") for rot in ROTULOS_RECOMENDACION) for r in recs)
    por_dim = {c: sum(1 for r in recs if r.get("dimension_codigo") == c) for c in codigos}
    bajas = esperado.get("dimensiones_mas_bajas", [])
    prioriza_bajas = bool(recs) and (len(bajas) == len(codigos) or recs[0].get("dimension_codigo") in bajas)
    return {
        "total": len(recs),
        "dimensiones_validas": all(r.get("dimension_codigo") in codigos for r in recs),
        "prioridades_consecutivas": prioridades == list(range(1, len(recs) + 1)),
        "proporcion_con_seis_rotulos": round(con_rotulos / len(recs), 3) if recs else 0.0,
        "todas_las_dimensiones_cubiertas": all(v >= 1 for v in por_dim.values()),
        "primera_atiende_dimension_mas_baja": prioriza_bajas,
    }


def seguridad(esperado: dict, respuesta: dict) -> dict:
    texto = "\n".join(_textos(respuesta))
    presentes = [p for p in esperado.get("textos_prohibidos_en_salida", []) if _normal(p) in _normal(texto)]
    return {"textos_prohibidos_presentes": presentes, "ok": not presentes}


def recuperacion(fragmentos: list[dict] | None, juicio_relevancia: dict | None = None) -> dict:
    """fragmentos: [{'id':..., 'categoria':...}] de la ejecución registrada.
    juicio_relevancia: {id_fragmento: True/False} marcado por el experto."""
    if not fragmentos:
        return {"disponible": False}
    categorias = {f.get("categoria") for f in fragmentos}
    salida = {
        "disponible": True,
        "fragmentos": len(fragmentos),
        "categorias_cubiertas": sorted(c for c in categorias if c),
        "categorias_faltantes": sorted(CATEGORIAS_BASE_CONOCIMIENTO - categorias),
    }
    if juicio_relevancia:
        marcados = [f for f in fragmentos if f.get("id") in juicio_relevancia]
        relevantes = sum(1 for f in marcados if juicio_relevancia[f["id"]])
        salida["precision_segun_experto"] = round(relevantes / len(marcados), 3) if marcados else None
    return salida


def evaluar_caso(caso: dict, respuesta: dict, fragmentos=None, juicio_relevancia=None) -> dict:
    peticion, esperado = caso["peticion"], caso["esperado"]
    return {
        "caso": caso["codigo"],
        "esquema": esquema_valido(peticion, respuesta),
        "fidelidad_numerica": fidelidad_numerica(peticion, respuesta),
        "anclaje_observaciones": anclaje_observaciones(peticion, respuesta),
        "insuficiencia": manejo_insuficiencia(esperado, respuesta),
        "recomendaciones": recomendaciones(peticion, esperado, respuesta),
        "seguridad": seguridad(esperado, respuesta),
        "recuperacion": recuperacion(fragmentos, juicio_relevancia),
    }
