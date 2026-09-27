import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from src.dominio.puertos.repositorio_sesion import RepositorioSesion

DURACION_SESION_MINUTOS = 30  # RF-47: cierre de sesión por inactividad, igual
# que trust4p-api-negocio — misma colección, mismo criterio de expiración.


class RepositorioMongoSesion(RepositorioSesion):
    """Solo lectura sobre `sesiones`: este servicio nunca crea, actualiza el
    contenido de o revoca una sesión. Renovar `expira_en` en cada
    verificación exitosa es la excepción — es el mismo mecanismo de
    ventana deslizante que aplica trust4p-api-negocio, y una actividad del
    administrador aquí debe contar igual que una allá."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["sesiones"]

    async def obtener_sesion_por_token(self, token: str) -> Optional[dict]:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return await self._coleccion.find_one_and_update(
            {
                "token_hash": token_hash,
                "expira_en": {"$gt": datetime.now(timezone.utc)},
            },
            {
                "$set": {
                    "expira_en": datetime.now(timezone.utc)
                    + timedelta(minutes=DURACION_SESION_MINUTOS)
                }
            },
            return_document=ReturnDocument.AFTER,
        )
