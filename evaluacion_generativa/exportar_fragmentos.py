"""C9: exporta, para cada caso, los fragmentos que recuperó el agente
(id, categoría y documento) desde ejecuciones_agente, para medir la
recuperación y para que el experto marque su relevancia.

Solo lee las ejecuciones de los casos de evaluación (diagnostico_id «c9-…»).
Uso: MONGO_URI=... python -m evaluacion_generativa.exportar_fragmentos resultados/2026-11-08
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


async def main(salida: Path):
    db = AsyncIOMotorClient(os.environ["MONGO_URI"])["trust4p"]
    async for e in db["ejecuciones_agente"].find({"diagnostico_id": {"$regex": "^c9-"}, "estado": "exitosa"}).sort("ejecutado_en", 1):
        ids = [ObjectId(i) for i in e.get("fragmentos_recuperados", []) if ObjectId.is_valid(i)]
        frags = [
            {"id": str(f["_id"]), "categoria": f.get("categoria"), "documento_id": f.get("documento_id"),
             "extracto": (f.get("contenido") or "")[:200]}
            async for f in db["fragmentos_conocimiento"].find({"_id": {"$in": ids}}, {"embedding": 0})
        ]
        codigo = e["diagnostico_id"].split("-")[1]
        (salida / f"{codigo}.fragmentos.json").write_text(json.dumps(frags, ensure_ascii=False, indent=1), encoding="utf-8")
        print(codigo, len(frags), "fragmentos")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
