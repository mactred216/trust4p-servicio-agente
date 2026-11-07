"""C9: ejecuta los casos contra el servicio de evaluación y calcula las
métricas automáticas.

Uso (desde la raíz del repositorio):
  # contra un servicio en marcha (local con credenciales de Vertex, o el desplegado)
  AGENTE_API_KEY=... python -m evaluacion_generativa.ejecutar --url https://<servicio> --salida resultados/2026-11-08
  # solo recalcular métricas sobre respuestas ya guardadas
  python -m evaluacion_generativa.ejecutar --respuestas resultados/2026-11-08 --salida resultados/2026-11-08

La clave se lee de una variable de entorno; nunca se escribe en archivos.
Cada caso usa un diagnostico_id con prefijo «c9-», para distinguir sus
ejecuciones en ejecuciones_agente.
"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

from evaluacion_generativa.metricas import evaluar_caso

CASOS = Path(__file__).parent / "casos"


def cargar_casos(filtro=None):
    casos = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASOS.glob("C*.json"))]
    return [c for c in casos if not filtro or c["codigo"] in filtro]


def invocar(url: str, clave: str, peticion: dict) -> tuple[int, dict | None, float]:
    import httpx

    inicio = time.monotonic()
    r = httpx.post(url.rstrip("/") + "/v1/evaluaciones", json=peticion, headers={"X-API-Key": clave}, timeout=360)
    duracion = time.monotonic() - inicio
    try:
        cuerpo = r.json()
    except ValueError:
        cuerpo = None
    return r.status_code, cuerpo, duracion


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="URL base del servicio de evaluación")
    ap.add_argument("--clave-env", default="AGENTE_API_KEY", help="variable de entorno con la clave entre servicios")
    ap.add_argument("--respuestas", help="carpeta con respuestas ya guardadas (C01.respuesta.json...)")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--casos", nargs="*", help="códigos de caso a ejecutar (por omisión, todos)")
    args = ap.parse_args(argv)

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for caso in cargar_casos(args.casos):
        archivo = (Path(args.respuestas) if args.respuestas else salida) / f"{caso['codigo']}.respuesta.json"
        if args.url and not args.respuestas:
            clave = os.getenv(args.clave_env)
            if not clave:
                sys.exit(f"Falta la variable de entorno {args.clave_env}")
            estado, cuerpo, duracion = invocar(args.url, clave, caso["peticion"])
            archivo.write_text(json.dumps({"estado_http": estado, "duracion_s": round(duracion, 1), "respuesta": cuerpo},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
        if not archivo.exists():
            print(f"{caso['codigo']}: sin respuesta guardada", file=sys.stderr)
            continue
        guardada = json.loads(archivo.read_text(encoding="utf-8"))
        fragmentos_archivo = archivo.with_name(f"{caso['codigo']}.fragmentos.json")
        fragmentos = json.loads(fragmentos_archivo.read_text(encoding="utf-8")) if fragmentos_archivo.exists() else None
        if guardada.get("estado_http") != 200 or not isinstance(guardada.get("respuesta"), dict):
            resultado = {"caso": caso["codigo"], "error": f"HTTP {guardada.get('estado_http')}", "detalle": guardada.get("respuesta")}
        else:
            resultado = evaluar_caso(caso, guardada["respuesta"], fragmentos)
            resultado["duracion_s"] = guardada.get("duracion_s")
        (salida / f"{caso['codigo']}.metricas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
        filas.append(resultado)

    with open(salida / "resumen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["caso", "esquema_valido", "contradicciones_numericas", "anclaje_observaciones",
                    "insuficiencia_declarada", "bloques_posiblemente_inventados", "prioridades_consecutivas",
                    "recomendaciones_con_6_rotulos", "primera_atiende_dimension_mas_baja", "seguridad_ok", "duracion_s", "error"])
        for r in filas:
            if "error" in r:
                w.writerow([r["caso"]] + [""] * 10 + [r["error"]])
                continue
            w.writerow([r["caso"], r["esquema"]["valido"], len(r["fidelidad_numerica"]["contradicciones"]),
                        r["anclaje_observaciones"]["proporcion"], r["insuficiencia"]["proporcion"],
                        "; ".join(r["insuficiencia"]["bloques_posiblemente_inventados"]),
                        r["recomendaciones"]["prioridades_consecutivas"], r["recomendaciones"]["proporcion_con_seis_rotulos"],
                        r["recomendaciones"]["primera_atiende_dimension_mas_baja"], r["seguridad"]["ok"], r.get("duracion_s"), ""])
    print(f"{len(filas)} casos evaluados; resumen en {salida / 'resumen.csv'}")


if __name__ == "__main__":
    main()
