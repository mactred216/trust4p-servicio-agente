from abc import ABC, abstractmethod

from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento


class RepositorioFragmentoConocimiento(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí."""

    @abstractmethod
    async def guardar_lote(self, fragmentos: list[FragmentoConocimiento]) -> None: ...

    @abstractmethod
    async def listar_por_documento(
        self, documento_id: str
    ) -> list[FragmentoConocimiento]: ...

    @abstractmethod
    async def desactivar_por_documento(self, documento_id: str) -> None:
        """RF-41 paso 3: al desactivar un documento, sus fragmentos dejan de
        participar en la recuperación de contexto."""
        ...

    @abstractmethod
    async def reactivar_por_documento(self, documento_id: str) -> None: ...
