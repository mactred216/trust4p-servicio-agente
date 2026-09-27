from abc import ABC, abstractmethod


class ClienteInferencia(ABC):
    """Puerto de salida hacia el proveedor del modelo de lenguaje."""

    @abstractmethod
    async def generar(self, instruccion: str) -> str:
        """Devuelve el texto crudo de la respuesta; el llamador decide cómo
        interpretarlo (RF-38 valida antes de confiar en él)."""
        ...
