from abc import ABC, abstractmethod


class ClienteEmbeddings(ABC):
    """Puerto de salida hacia el proveedor de vectorización de texto."""

    @abstractmethod
    async def generar(self, texto: str) -> list[float]: ...
