import asyncio
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

# Un límite de tasa del proveedor (429 RESOURCE_EXHAUSTED) no es una petición
# mal formada sino una petición que llegó temprano: la capacidad compartida de
# Vertex AI tarda en ceder mucho más que los pocos segundos que bastan ante un
# error de red. Por eso a ese caso, y solo a ese, se le conceden más intentos y
# esperas más largas; con la espera base de 2 s la secuencia es 8, 16, 32 y 64
# segundos, que cabe holgadamente en el plazo de 300 s del cliente de la API.
MAXIMO_INTENTOS_LIMITE_TASA = 5
FACTOR_ESPERA_LIMITE_TASA = 4.0

# Espera base (segundos) entre reintentos ante un error del proveedor; se duplica
# en cada intento. Los 429 de Vertex AI suelen ser picos transitorios de
# concurrencia: reintentar al instante agota los intentos sin darles tiempo
# de ceder (ASR-02). 0 desactiva la espera (pruebas).
ESPERA_REINTENTO_SEGUNDOS = 2.0
PROVEEDOR_INFERENCIA = "google-vertex-ai"


def _es_limite_de_tasa(error: Exception) -> bool:
    """Reconoce el 429 del proveedor por su mensaje, sin acoplar el caso de
    uso al SDK concreto que lo produce (ADR-002)."""
    texto = str(error).upper()
    return "429" in texto or "RESOURCE_EXHAUSTED" in texto


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
        modelo: str = "gpt-oss-120b-maas",
        proveedor: str = PROVEEDOR_INFERENCIA,
        espera_reintento_segundos: float = 0.0,
    ):
        self._fragmentos = repo_fragmento
        self._embeddings = cliente_embeddings
        self._inferencia = cliente_inferencia
        self._ejecuciones = repo_ejecucion
        self._modelo = modelo
        self._proveedor = proveedor
        self._espera_reintento = espera_reintento_segundos

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
        limite_intentos = MAXIMO_INTENTOS
        intento = 0
        while intento < limite_intentos:
            intento += 1
            es_ultimo_intento = intento == limite_intentos
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
                if _es_limite_de_tasa(e):
                    limite_intentos = MAXIMO_INTENTOS_LIMITE_TASA
                    factor_espera = FACTOR_ESPERA_LIMITE_TASA
                else:
                    factor_espera = 1.0
                es_ultimo_intento = intento == limite_intentos
                await self._registrar_intento(
                    solicitud,
                    intento,
                    peticion_auditoria,
                    ids_fragmentos,
                    estado="fallida" if es_ultimo_intento else "reintento",
                    mensaje_error=motivo_fallo,
                )
                if not es_ultimo_intento and self._espera_reintento > 0:
                    await asyncio.sleep(
                        self._espera_reintento * factor_espera * 2 ** (intento - 1)
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
            f"Se agotaron los {limite_intentos} intentos: {motivo_fallo}"
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
