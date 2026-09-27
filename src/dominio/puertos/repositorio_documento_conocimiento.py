from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.documento_conocimiento import DocumentoConocimiento


class RepositorioDocumentoConocimiento(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí."""

    @abstractmethod
    async def guardar(
        self, documento: DocumentoConocimiento
    ) -> DocumentoConocimiento: ...

    @abstractmethod
    async def obtener_por_id(
        self, documento_id: str
    ) -> Optional[DocumentoConocimiento]: ...

    @abstractmethod
    async def actualizar(self, documento: DocumentoConocimiento) -> None: ...

    @abstractmethod
    async def listar(self) -> list[DocumentoConocimiento]: ...
