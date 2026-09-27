from abc import ABC, abstractmethod


class ExtractorTexto(ABC):
    """Puerto de salida hacia el lector del formato de archivo del
    documento cargado (RF-41 paso 1: 'valida el formato permitido')."""

    @abstractmethod
    def extraer(self, contenido: bytes) -> str: ...
