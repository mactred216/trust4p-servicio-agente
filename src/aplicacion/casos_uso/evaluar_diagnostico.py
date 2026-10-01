import json

from src.aplicacion.compositor_contexto import (
    VERSION_PLANTILLA_INSTRUCCIONES, componer_instruccion,
    construir_peticion_auditoria, recuperar_contexto)
from src.dominio.entidades.ejecucion_agente import EjecucionAgente
from src.dominio.entidades.evaluacion import (RespuestaAgente,
                                              SolicitudEvaluacion)
from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings
from src.dominio.puertos.cliente_inferencia import (ClienteInferencia,
                                                    ResultadoInferencia)
from src.dominio.puertos.repositorio_ejecucion_agente import \
    RepositorioEjecucionAgente
from src.dominio.puertos.repositorio_fragmento_conocimiento import \
    RepositorioFragmentoConocimiento
from src.dominio.servicios.saneador import sanear_solicitud
from src.dominio.servicios.validador_esquema import (RespuestaAgenteInvalida,
                                                     validar_respuesta_agente)

MAXIMO_INTENTOS = 3
PROVEEDOR_INFERENCIA = "google-vertex-ai"


class EvaluacionFallida(Exception):
    """RF-38: se agotaron los reintentos sin obtener una respuesta válida."""

    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


class EvaluarDiagnostico:
    """RF-36 a RF-40: compone el contexto, invoca al agente, valida su
    respuesta contra el esquema y registra cada intento en la bitácora de
    auditoría (RF-42/43). No persiste el resultado — eso lo hace
    trust4p-api-negocio, único responsable de escribir el diagnóstico
    (ADR-005/3.4.2)."""

    def __init__(
        self,
        repo_fragmento: RepositorioFragmentoConocimiento,
        cliente_embeddings: ClienteEmbeddings,
        cliente_inferencia: ClienteInferencia,
        repo_ejecucion: RepositorioEjecucionAgente,
        modelo: str = "qwen3-next-80b-a3b-instruct-maas",
        proveedor: str = PROVEEDOR_INFERENCIA,
    ):
        self._fragmentos = repo_fragmento
        self._embeddings = cliente_embeddings
        self._inferencia = cliente_inferencia
        self._ejecuciones = repo_ejecucion
        self._modelo = modelo
        self._proveedor = proveedor

    async def ejecutar(self, solicitud: SolicitudEvaluacion) -> RespuestaAgente:
        sanear_solicitud(solicitud)

        codigos_dimensiones = {
            d.codigo for d in solicitud.resultado_calculo.dimensiones
        }
        fragmentos = await recuperar_contexto(
            solicitud, self._fragmentos, self._embeddings
        )
        instruccion = componer_instruccion(solicitud, fragmentos)
        peticion_auditoria = construir_peticion_auditoria(solicitud, fragmentos)
        ids_fragmentos = [f.id for f in fragmentos if f.id is not None]

        motivo_fallo = "sin intentos"
        for intento in range(1, MAXIMO_INTENTOS + 1):
            es_ultimo_intento = intento == MAXIMO_INTENTOS
            resultado_inferencia: ResultadoInferencia | None = None
            try:
                resultado_inferencia = await self._inferencia.generar(instruccion)
                datos = json.loads(resultado_inferencia.texto)
                respuesta_agente = validar_respuesta_agente(datos, codigos_dimensiones)
            except (json.JSONDecodeError, RespuestaAgenteInvalida) as e:
                motivo_fallo = str(e)
                await self._registrar_intento(
                    solicitud,
                    intento,
                    peticion_auditoria,
                    ids_fragmentos,
                    estado="fallida" if es_ultimo_intento else "reintento",
                    mensaje_error=motivo_fallo,
                    resultado_inferencia=resultado_inferencia,
                )
                continue
            except Exception as e:
                # Cualquier falla del proveedor (red, límite de tasa,
                # tiempo de espera) se trata igual que una respuesta
                # inválida: se reintenta hasta MAXIMO_INTENTOS antes de
                # marcar el diagnóstico como fallido, nunca se propaga como
                # un error 500 sin más.
                motivo_fallo = f"Error del proveedor de inferencia: {e}"
                await self._registrar_intento(
                    solicitud,
                    intento,
                    peticion_auditoria,
                    ids_fragmentos,
                    estado="fallida" if es_ultimo_intento else "reintento",
                    mensaje_error=motivo_fallo,
                )
                continue

            await self._registrar_intento(
                solicitud,
                intento,
                peticion_auditoria,
                ids_fragmentos,
                estado="exitosa",
                respuesta=datos,
                resultado_inferencia=resultado_inferencia,
            )
            return respuesta_agente

        raise EvaluacionFallida(
            f"Se agotaron los {MAXIMO_INTENTOS} intentos: {motivo_fallo}"
        )

    async def _registrar_intento(
        self,
        solicitud: SolicitudEvaluacion,
        intento: int,
        peticion_auditoria: dict,
        ids_fragmentos: list[str],
        estado: str,
        respuesta: dict | None = None,
        mensaje_error: str | None = None,
        resultado_inferencia: ResultadoInferencia | None = None,
    ) -> None:
        await self._ejecuciones.registrar(
            EjecucionAgente(
                id=None,
                diagnostico_id=solicitud.diagnostico_id,
                intento=intento,
                peticion=peticion_auditoria,
                fragmentos_recuperados=ids_fragmentos,
                proveedor=self._proveedor,
                modelo=self._modelo,
                version_prompt=VERSION_PLANTILLA_INSTRUCCIONES,
                modelo_version=solicitud.modelo_version,
                estado=estado,
                respuesta=respuesta,
                mensaje_error=mensaje_error,
                tokens_entrada=(
                    resultado_inferencia.tokens_entrada
                    if resultado_inferencia
                    else None
                ),
                tokens_salida=(
                    resultado_inferencia.tokens_salida if resultado_inferencia else None
                ),
                duracion_ms=(
                    resultado_inferencia.duracion_ms if resultado_inferencia else None
                ),
            )
        )
