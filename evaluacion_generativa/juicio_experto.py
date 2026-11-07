"""C9: consolida la plantilla de juicio experto (una fila por caso, evaluador
y criterio, puntaje de 1 a 4).

Escala: 1 = inaceptable, 2 = insuficiente, 3 = aceptable, 4 = adecuado.
Con dos evaluadores informa el acuerdo exacto, el acuerdo a un punto y la
kappa de Cohen ponderada cuadrática.

Uso: python -m evaluacion_generativa.juicio_experto juicio_diligenciado.csv
"""
import csv
import sys
from collections import defaultdict
from statistics import mean


def leer(ruta):
    filas = []
    with open(ruta, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("puntaje_1_a_4") or "").strip():
                p = int(r["puntaje_1_a_4"])
                if p not in (1, 2, 3, 4):
                    raise ValueError(f"Puntaje fuera de escala en {r}")
                filas.append({**r, "puntaje": p})
    return filas


def kappa_ponderada(pares, k=4):
    """Kappa de Cohen con pesos cuadráticos para dos evaluadores."""
    if not pares:
        return None
    n = len(pares)
    obs = [[0] * k for _ in range(k)]
    for a, b in pares:
        obs[a - 1][b - 1] += 1
    fa = [sum(obs[i]) for i in range(k)]
    fb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    po = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w[i][j] * fa[i] * fb[j] for i in range(k) for j in range(k)) / (n * n)
    return None if pe == 0 else round(1 - po / pe, 3)


def consolidar(filas):
    por_criterio = defaultdict(list)
    por_item = defaultdict(dict)
    for r in filas:
        por_criterio[r["criterio"]].append(r["puntaje"])
        por_item[(r["caso"], r["criterio"])][r["evaluador"]] = r["puntaje"]
    resumen = {
        c: {"n": len(v), "media": round(mean(v), 2), "proporcion_aceptable": round(sum(x >= 3 for x in v) / len(v), 3)}
        for c, v in sorted(por_criterio.items())
    }
    evaluadores = sorted({r["evaluador"] for r in filas})
    acuerdo = None
    if len(evaluadores) == 2:
        a, b = evaluadores
        pares = [(d[a], d[b]) for d in por_item.values() if a in d and b in d]
        if pares:
            acuerdo = {
                "items": len(pares),
                "acuerdo_exacto": round(sum(x == y for x, y in pares) / len(pares), 3),
                "acuerdo_a_un_punto": round(sum(abs(x - y) <= 1 for x, y in pares) / len(pares), 3),
                "kappa_ponderada": kappa_ponderada(pares),
            }
    return {"evaluadores": evaluadores, "por_criterio": resumen, "acuerdo": acuerdo}


if __name__ == "__main__":
    import json

    print(json.dumps(consolidar(leer(sys.argv[1])), ensure_ascii=False, indent=1))
