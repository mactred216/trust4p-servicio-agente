import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from src.api.routers import documentos, ejecuciones, evaluaciones
from src.infraestructura.persistencia.conexion import obtener_base_datos
from src.infraestructura.persistencia.inicializacion import crear_indices

load_dotenv()


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Arranque: asegura los indices de las colecciones del servicio
    (idempotente); si la base no responde no se detiene el proceso."""
    try:
        await crear_indices(obtener_base_datos())
    except Exception:
        logging.getLogger("trust4p.arranque").exception(
            "No se pudieron crear los indices"
        )
    yield


app = FastAPI(
    title="Trust 4P - Servicio de Evaluación Asistida", lifespan=ciclo_de_vida
)

app.include_router(documentos.router, prefix="/v1")
app.include_router(evaluaciones.router, prefix="/v1")
app.include_router(ejecuciones.router, prefix="/v1")


@app.get("/salud")
async def salud():
    return {"estado": "operativo"}
