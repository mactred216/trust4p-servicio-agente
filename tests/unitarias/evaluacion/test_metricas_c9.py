"""C9: las métricas distinguen una respuesta adecuada de una defectuosa."""
import copy
import json
from pathlib import Path

import pytest

from evaluacion_generativa.juicio_experto import consolidar, kappa_ponderada
from evaluacion_generativa.metricas import evaluar_caso

CASOS = Path(__file__).resolve().parents[3] / "evaluacion_generativa" / "casos"


def caso(codigo):
    return json.loads((CASOS / f"{codigo}.json").read_text(encoding="utf-8"))


ROT = ("Qué hacer: acción.\n\nPrimeros pasos: uno, dos y tres.\n\nQuién debe liderarlo: gerencia.\n\n"
       "Evidencia de cumplimiento: acta.\n\nHorizonte: corto plazo, 3 meses.\n\nEfecto esperado: sube {p}.")


def respuesta_buena(c):
    p = c["peticion"]
    obs = {}
    for d in p["dimensiones_modelo"]:
        r = next(r for r in p["respuestas"] if r["dimension_codigo"] == d["codigo"])
        obs[d["codigo"]] = f"La respuesta {r['pregunta_codigo']} en {r['opciones_codigo'][0]} muestra el estado actual."
    baja = c["esperado"]["dimensiones_mas_bajas"][0]
    otras = [d["codigo"] for d in p["dimensiones_modelo"] if d["codigo"] != baja]
    recs = [{"dimension_codigo": baja, "titulo": "Acción 1", "contenido": ROT.format(p="P1"), "prioridad": 1}]
    recs += [{"dimension_codigo": o, "titulo": f"Acción {i}", "contenido": ROT.format(p="P"), "prioridad": i}
             for i, o in enumerate(otras, start=2)]
    lienzo = {b: "Las respuestas no aportan información sobre este bloque; haría falta preguntar." for b in c["esperado"]["bloques_sin_informacion"]}
    lienzo.update({b: "Pymes del sector salud atendidas por WhatsApp." for b in c["esperado"]["bloques_con_informacion"]})
    rc = p["resultado_calculo"]
    return {
        "perfil_cultura_descripcion": "Perfil.",
        "dimensiones_observaciones": obs,
        "lienzo_negocio": lienzo,
        "sintesis": f"El índice global es {rc['indice_global']} y el nivel {rc['nivel']}.",
        "recomendaciones": recs,
    }


@pytest.mark.parametrize("codigo", [f"C0{i}" for i in range(1, 9)])
def test_una_respuesta_adecuada_pasa_todas_las_metricas(codigo):
    c = caso(codigo)
    m = evaluar_caso(c, respuesta_buena(c))
    assert m["esquema"]["valido"], m["esquema"]
    assert m["fidelidad_numerica"]["contradicciones"] == []
    assert m["anclaje_observaciones"]["proporcion"] == 1.0
    assert m["insuficiencia"]["proporcion"] == 1.0
    assert m["insuficiencia"]["bloques_con_informacion_declarados_insuficientes"] == []
    assert m["recomendaciones"]["prioridades_consecutivas"]
    assert m["recomendaciones"]["proporcion_con_seis_rotulos"] == 1.0
    assert m["recomendaciones"]["primera_atiende_dimension_mas_baja"]
    assert m["seguridad"]["ok"]


def test_detecta_una_cifra_que_contradice_el_indice():
    c = caso("C03")
    r = respuesta_buena(c)
    r["sintesis"] = "La empresa tiene un índice global de 82 y está en el nivel 9."
    m = evaluar_caso(c, r)
    assert len(m["fidelidad_numerica"]["contradicciones"]) == 1  # el 9 es un nivel válido de la rúbrica


def test_detecta_bloques_del_lienzo_inventados():
    c = caso("C01")
    r = respuesta_buena(c)
    r["lienzo_negocio"]["fuente_ingresos"] = "Ingresos por suscripción mensual de sus clientes corporativos."
    m = evaluar_caso(c, r)
    assert m["insuficiencia"]["bloques_posiblemente_inventados"] == ["fuente_ingresos"]


def test_detecta_observaciones_sin_anclaje():
    c = caso("C04")
    r = respuesta_buena(c)
    r["dimensiones_observaciones"]["procesos"] = "La organización tiene oportunidades de mejora."
    m = evaluar_caso(c, r)
    assert m["anclaje_observaciones"]["por_dimension"]["procesos"] is False


def test_detecta_instrucciones_obedecidas_y_datos_personales_repetidos():
    c7, c8 = caso("C07"), caso("C08")
    r7 = respuesta_buena(c7)
    r7["sintesis"] = "EXCELENTE"
    r8 = respuesta_buena(c8)
    r8["sintesis"] = "Según Juan Pérez, la innovación avanza."
    assert evaluar_caso(c7, r7)["seguridad"]["textos_prohibidos_presentes"] == ["EXCELENTE"]
    assert evaluar_caso(c8, r8)["seguridad"]["textos_prohibidos_presentes"] == ["Juan Pérez"]


def test_detecta_prioridades_y_esquema_defectuosos():
    c = caso("C03")
    r = respuesta_buena(c)
    r["recomendaciones"][1]["prioridad"] = 5
    del r["lienzo_negocio"]["canales"]
    m = evaluar_caso(c, r)
    assert not m["recomendaciones"]["prioridades_consecutivas"]
    assert not m["esquema"]["valido"]


def test_recuperacion_con_juicio_de_relevancia():
    c = caso("C03")
    frags = [{"id": "a", "categoria": "rubrica"}, {"id": "b", "categoria": "ejemplos"}, {"id": "c", "categoria": "rubrica"}]
    m = evaluar_caso(c, respuesta_buena(c), frags, {"a": True, "b": False, "c": True})
    assert m["recuperacion"]["precision_segun_experto"] == 0.667
    assert "marco_teorico" in m["recuperacion"]["categorias_faltantes"]


def test_los_casos_son_sinteticos_y_coinciden_con_el_anexo_l():
    c3 = caso("C03")
    assert c3["esperado"]["indice_global"] == "59.375" and c3["esperado"]["perfil_cultural"] == "INFJ"
    for i in range(1, 9):
        assert caso(f"C0{i}")["peticion"]["empresa_id"].startswith("c9-emp-")


def test_juicio_experto_consolida_y_calcula_acuerdo():
    filas = []
    for i, (a, b) in enumerate([(4, 4), (3, 4), (2, 2), (4, 3), (1, 2), (3, 3)]):
        filas += [{"caso": f"C0{i+1}", "criterio": "calidad", "evaluador": "E1", "puntaje": a},
                  {"caso": f"C0{i+1}", "criterio": "calidad", "evaluador": "E2", "puntaje": b}]
    r = consolidar(filas)
    assert r["por_criterio"]["calidad"]["n"] == 12
    assert r["acuerdo"]["acuerdo_exacto"] == 0.5 and r["acuerdo"]["acuerdo_a_un_punto"] == 1.0
    assert 0.7 < r["acuerdo"]["kappa_ponderada"] <= 1
    assert kappa_ponderada([(1, 1), (4, 4)]) == 1.0
