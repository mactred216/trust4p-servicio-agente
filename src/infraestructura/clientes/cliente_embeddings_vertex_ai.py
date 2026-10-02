import os

from langchain_google_vertexai import VertexAIEmbeddings

from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings


class ClienteEmbeddingsVertexAI(ClienteEmbeddings):
    """Adaptador hacia el modelo de embeddings de texto de Vertex AI,
    vectorizado a través de LangChain (igual que la carga y fragmentación
    de documentos de RF-41)."""

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
        self._cliente: VertexAIEmbeddings | None = None

    def _obtener_cliente(self) -> VertexAIEmbeddings:
        if self._cliente is None:
            self._cliente = VertexAIEmbeddings(
                model_name=self._modelo_nombre,
                project=self._project,
                location=self._location,
            )
        return self._cliente

    async def generar(self, texto: str) -> list[float]:
        return await self._obtener_cliente().aembed_query(texto)
