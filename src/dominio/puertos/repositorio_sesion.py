from abc import ABC, abstractmethod
from typing import Optional


class RepositorioSesion(ABC):
    """Puerto de solo lectura sobre la colección `sesiones`, propiedad de
    trust4p-api-negocio (comparten la misma base de datos). Este servicio
    nunca crea, actualiza ni revoca sesiones — solo verifica una ya
    existente, igual que hace `requiere_rol` en el servicio de negocio."""

    @abstractmethod
    async def obtener_sesion_por_token(self, token: str) -> Optional[dict]: ...
