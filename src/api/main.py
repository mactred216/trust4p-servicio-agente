from dotenv import load_dotenv
from fastapi import FastAPI

from src.api.routers import documentos, evaluaciones

load_dotenv()

app = FastAPI(title="Trust 4P - Servicio de Evaluación Asistida")

app.include_router(documentos.router, prefix="/v1")
app.include_router(evaluaciones.router, prefix="/v1")


@app.get("/salud")
async def salud():
    return {"estado": "operativo"}
