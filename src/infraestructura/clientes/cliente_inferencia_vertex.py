import asyncio
import os
import time

from google import genai
from google.genai import types

from src.dominio.puertos.cliente_inferencia import (ClienteInferencia,
                                                    ResultadoInferencia)

# El modelo se sirve como servicio gestionado de Vertex AI por el endpoint
# 'global'. Qwen3-Next-80B-Instruct (ADR-007) dejó de existir el 21-oct-2026,
# cuando Google retiró los cuatro endpoints gestionados de Qwen (deprecación
# del 21-jul-2026): desde entonces la API respondía 404 «Publisher model ...
# was not found» y toda evaluación quedaba fallida. Lo sustituye gpt-oss-120b,
# también de pesos abiertos (ADR-021). El identificador sigue siendo
# configurable con VERTEX_INFERENCE_MODEL.
MODELO_POR_DEFECTO = "publishers/openai/models/gpt-oss-120b-maas"


class ClienteInferenciaVertex(ClienteInferencia):
    """Adaptador real hacia un modelo de lenguaje de pesos abiertos servido
    como servicio gestionado de Vertex AI (ADR-007, ADR-021). Usa el SDK
    unificado google-genai — el SDK vertexai.generative_models está
    deprecado y no debía usarse para código nuevo."""

    def __init__(
        self,
        project: str | None = None,
        location: str | None = None,
        modelo: str | None = None,
    ):
        self._project = project or os.getenv("GCP_PROJECT_ID")
        self._location = location or os.getenv("GCP_INFERENCIA_REGION", "global")
        self._modelo = modelo or os.getenv("VERTEX_INFERENCE_MODEL", MODELO_POR_DEFECTO)
        self._cliente = None

    @property
    def nombre_modelo(self) -> str:
        """Identificador corto del modelo, tal como se registra en la bitácora
        de ejecuciones (p. ej. «gpt-oss-120b-maas»)."""
        return self._modelo.split("/models/")[-1]

    def _obtener_cliente(self) -> genai.Client:
        if self._cliente is None:
            self._cliente = genai.Client(
                vertexai=True, project=self._project, location=self._location
            )
        return self._cliente

    async def generar(self, instruccion: str) -> ResultadoInferencia:
        return await asyncio.to_thread(self._generar_sincrono, instruccion)

    def _generar_sincrono(self, instruccion: str) -> ResultadoInferencia:
        cliente = self._obtener_cliente()
        inicio = time.monotonic()
        respuesta = cliente.models.generate_content(
            model=self._modelo,
            contents=instruccion,
            # El formato JSON se exige en el texto de la instrucción y RF-38
            # valida el resultado en el propio código. No se fuerza
            # response_mime_type: gpt-oss-120b lo trata de forma errática
            # (comprobado en vivo el 25-oct-2026, a veces devolvía basura) y
            # tampoco se delega a la API la validación de la estructura.
        )
        duracion_ms = int((time.monotonic() - inicio) * 1000)
        uso = respuesta.usage_metadata
        return ResultadoInferencia(
            texto=respuesta.text,
            tokens_entrada=uso.prompt_token_count if uso else None,
            tokens_salida=uso.candidates_token_count if uso else None,
            duracion_ms=duracion_ms,
        )
