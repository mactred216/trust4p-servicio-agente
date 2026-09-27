import asyncio
import os

import vertexai
from vertexai.language_models import TextEmbeddingModel

from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings


class ClienteEmbeddingsVertexAI(ClienteEmbeddings):
    """Adaptador real hacia el modelo de embeddings de texto de Vertex AI
    (propio de Google, no requiere Model Garden). No verificado todavía
    contra el servicio real — pendiente de que exista GOOGLE_APPLICATION
    _CREDENTIALS / `gcloud auth application-default login` en el entorno."""

    def __init__(
        self,
        project: str | None = None,
        location: str | None = None,
        modelo: str | None = None,
    ):
        self._project = project or os.getenv("GCP_PROJECT_ID")
        self._location = location or os.getenv("GCP_REGION", "us-central1")
        self._modelo_nombre = modelo or os.getenv(
            "VERTEX_EMBEDDING_MODEL", "text-embedding-005"
        )
        self._modelo = None

    def _cargar_modelo(self) -> TextEmbeddingModel:
        if self._modelo is None:
            vertexai.init(project=self._project, location=self._location)
            self._modelo = TextEmbeddingModel.from_pretrained(self._modelo_nombre)
        return self._modelo

    async def generar(self, texto: str) -> list[float]:
        return await asyncio.to_thread(self._generar_sincrono, texto)

    def _generar_sincrono(self, texto: str) -> list[float]:
        modelo = self._cargar_modelo()
        resultado = modelo.get_embeddings([texto])
        return resultado[0].values
