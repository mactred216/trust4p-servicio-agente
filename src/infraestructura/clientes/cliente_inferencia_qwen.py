import asyncio
import os

from google import genai
from google.genai import types

from src.dominio.puertos.cliente_inferencia import ClienteInferencia

# El modelo solo está disponible vía el endpoint 'global' de Vertex AI, no
# en una región regular como us-central1 (confirmado en vivo 2026-09-27:
# 'Publisher model ... is not available in region us-central1' / 'only
# available via global endpoint' contra us-east5) — distinto de la región
# usada para el modelo de embeddings.
MODELO_POR_DEFECTO = "publishers/qwen/models/qwen3-next-80b-a3b-instruct-maas"


class ClienteInferenciaQwen(ClienteInferencia):
    """Adaptador real hacia Qwen3-Next-80B-Instruct como servicio gestionado
    de Vertex AI (ADR-007). Usa el SDK unificado google-genai — el SDK
    vertexai.generative_models funciona pero está deprecado (aviso de
    retiro para el 24 de junio de 2026, ya vencido en la fecha de esta
    sesión) y no debía usarse para código nuevo."""

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

    def _obtener_cliente(self) -> genai.Client:
        if self._cliente is None:
            self._cliente = genai.Client(
                vertexai=True, project=self._project, location=self._location
            )
        return self._cliente

    async def generar(self, instruccion: str) -> str:
        return await asyncio.to_thread(self._generar_sincrono, instruccion)

    def _generar_sincrono(self, instruccion: str) -> str:
        cliente = self._obtener_cliente()
        respuesta = cliente.models.generate_content(
            model=self._modelo,
            contents=instruccion,
            # Nota: se confirmó en vivo que este modelo NO respeta
            # response_schema (devuelve JSON con claves distintas a las
            # pedidas) — el formato JSON se exige en el texto de la
            # instrucción, y RF-38 valida el resultado en el propio código,
            # no delegando la validación de estructura a la API.
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return respuesta.text
