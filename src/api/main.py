from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI(title="Trust 4P - Servicio de Evaluación Asistida")


@app.get("/salud")
async def salud():
    return {"estado": "operativo"}
