from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoInferencia:
    """RNF-11/RNF-21: además del texto, se registran los indicadores de
    costo y desempeño de la invocación para la auditoría (ejecuciones_agente)."""

    texto: str
    tokens_entrada: Optional[int]
    tokens_salida: Optional[int]
    duracion_ms: int


class ClienteInferencia(ABC):
    """Puerto de salida hacia el proveedor del modelo de lenguaje."""

    @abstractmethod
    async def generar(self, instruccion: str) -> ResultadoInferencia:
        """Devuelve el texto crudo de la respuesta; el llamador decide cómo
        interpretarlo (RF-38 valida antes de confiar en él)."""
        ...
