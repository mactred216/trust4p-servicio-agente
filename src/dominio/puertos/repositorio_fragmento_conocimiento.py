from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.fragmento_conocimiento import FragmentoConocimiento


class RepositorioFragmentoConocimiento(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí."""

    @abstractmethod
    async def guardar_lote(self, fragmentos: list[FragmentoConocimiento]) -> None: ...

    @abstractmethod
    async def buscar_por_similitud(
        self,
        embedding: list[float],
        categoria: Optional[str] = None,
        limite: int = 5,
    ) -> list[FragmentoConocimiento]:
        """ADR-004/ASR-15: recuperación por similitud vectorial, restringida
        a fragmentos activos y, opcionalmente, a una categoría."""
        ...

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
