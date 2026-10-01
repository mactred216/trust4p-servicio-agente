from src.dominio.entidades.ejecucion_agente import EjecucionAgente
from src.dominio.puertos.repositorio_ejecucion_agente import \
    RepositorioEjecucionAgente


class ConsultarEjecucionesAgente:
    """RF-42: recupera la bitácora de intentos de evaluación de un
    diagnóstico, para que el administrador consulte petición y respuesta de
    cada uno en modo de solo lectura."""

    def __init__(self, repo_ejecucion: RepositorioEjecucionAgente):
        self._ejecuciones = repo_ejecucion

    async def ejecutar(self, diagnostico_id: str) -> list[EjecucionAgente]:
        return await self._ejecuciones.listar_por_diagnostico(diagnostico_id)
