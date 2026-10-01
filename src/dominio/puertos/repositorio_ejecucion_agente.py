from abc import ABC, abstractmethod

from src.dominio.entidades.ejecucion_agente import EjecucionAgente


class RepositorioEjecucionAgente(ABC):
    """Puerto del dominio. Colección de solo anexado (R-11 estilo
    'auditoria'): no se expone ningún método de actualización o eliminación
    — la ausencia del método hace la regla imposible de violar por
    accidente, mismo patrón que trust4p-api-negocio usa para 'auditoria'."""

    @abstractmethod
    async def registrar(self, ejecucion: EjecucionAgente) -> EjecucionAgente: ...

    @abstractmethod
    async def listar_por_diagnostico(
        self, diagnostico_id: str
    ) -> list[EjecucionAgente]:
        """RF-42: todos los intentos registrados para un diagnóstico, en el
        orden en que ocurrieron, para que el administrador los revise."""
        ...
