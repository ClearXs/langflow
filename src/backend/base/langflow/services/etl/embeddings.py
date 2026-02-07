"""Embedding service for generating vector embeddings.

Supports multiple embedding providers:
- OpenAI: text-embedding-3-small (1536 dimensions)
- Cohere: embed-english-v3.0
- SentenceTransformers: Local models
"""

import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(
        self,
        model: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
        dimension: int = 1536
    ):
        """Initialize embedding service.

        Args:
            model: Model provider (openai, cohere, sentence-transformers)
            api_key: API key for the provider
            base_url: Custom base URL for OpenAI-compatible APIs
            dimension: Expected embedding dimension
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.dimension = dimension
        self._embedder = None

    def _get_embedder(self):
        """Get or create embedder (lazy loading)."""
        if self._embedder is not None:
            return self._embedder

        try:
            from chonkie import AutoEmbeddings

            logger.info(f"Initializing embedder: {self.model}")

            self._embedder = AutoEmbeddings.get_embeddings(
                model=self.model,
                api_key=self.api_key,
                dimension=self.dimension
            )

            logger.info(f"Embedder initialized: {self.model}")
            return self._embedder

        except ImportError:
            logger.warning("Chonkie AutoEmbeddings not available, using fallback")
            return self._get_fallback_embedder()
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")
            return self._get_fallback_embedder()

    def _get_fallback_embedder(self):
        """Fallback embedder using OpenAI directly."""
        if self.model == "openai":
            try:
                from openai import AsyncOpenAI

                logger.info("Using OpenAI embedder fallback")

                # Initialize with custom base_url if provided
                if self.base_url:
                    logger.info(f"Using custom base URL: {self.base_url}")
                    self._embedder = AsyncOpenAI(
                        api_key=self.api_key,
                        base_url=self.base_url
                    )
                else:
                    self._embedder = AsyncOpenAI(api_key=self.api_key)

                return self._embedder

            except ImportError:
                logger.error("OpenAI library not available")
                return None

        elif self.model == "cohere":
            try:
                import cohere

                logger.info("Using Cohere embedder fallback")
                self._embedder = cohere.AsyncClient(self.api_key)
                return self._embedder

            except ImportError:
                logger.error("Cohere library not available")
                return None

        elif self.model == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer

                from langflow.services.etl.config import etl_config

                logger.info("Using SentenceTransformers fallback")
                self._embedder = SentenceTransformer(
                    etl_config.get_sentence_transformer_model(),
                    device=etl_config.get_sentence_transformer_device()
                )
                return self._embedder

            except ImportError:
                logger.error("SentenceTransformers library not available")
                return None

        return None

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.dimension

        try:
            embedder = self._get_embedder()

            if embedder is None:
                raise RuntimeError("No embedder available")

            # Try Chonkie AutoEmbeddings first
            if hasattr(embedder, "embed"):
                embedding = embedder.embed(text)
                return embedding if isinstance(embedding, list) else embedding.tolist()

            # Fallback to specific providers
            if self.model == "openai":
                from langflow.services.etl.config import etl_config

                response = await embedder.embeddings.create(
                    model=etl_config.get_openai_embedding_model(),
                    input=text
                )
                return response.data[0].embedding

            if self.model == "cohere":
                from langflow.services.etl.config import etl_config

                response = await embedder.embed(
                    texts=[text],
                    model=etl_config.get_cohere_embedding_model()
                )
                return response.embeddings[0]

            if self.model == "sentence-transformers":
                embedding = embedder.encode(text, convert_to_tensor=False)
                return embedding.tolist()

            raise RuntimeError(f"Unsupported embedding model: {self.model}")

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            logger.warning("All texts are empty")
            return [[0.0] * self.dimension] * len(texts)

        try:
            embedder = self._get_embedder()

            if embedder is None:
                raise RuntimeError("No embedder available")

            # Try Chonkie AutoEmbeddings batch processing
            if hasattr(embedder, "embed_batch"):
                embeddings = embedder.embed_batch(valid_texts)
                return [
                    emb if isinstance(emb, list) else emb.tolist()
                    for emb in embeddings
                ]

            # Fallback to specific providers
            if self.model == "openai":
                from langflow.services.etl.config import etl_config

                response = await embedder.embeddings.create(
                    model=etl_config.get_openai_embedding_model(),
                    input=valid_texts
                )
                return [item.embedding for item in response.data]

            if self.model == "cohere":
                from langflow.services.etl.config import etl_config

                response = await embedder.embed(
                    texts=valid_texts,
                    model=etl_config.get_cohere_embedding_model()
                )
                return response.embeddings

            if self.model == "sentence-transformers":
                embeddings = embedder.encode(valid_texts, convert_to_tensor=False)
                return [emb.tolist() for emb in embeddings]

            # Final fallback: sequential single-text embedding
            logger.warning("Using sequential embedding (slow)")
            return [await self.embed_text(text) for text in valid_texts]

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise RuntimeError(f"Failed to generate batch embeddings: {e}") from e


# Global instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service instance."""
    global _embedding_service

    if _embedding_service is None:
        from langflow.services.etl.config import etl_config

        embedding_model = etl_config.get_embedding_model()
        api_key = etl_config.get_api_key(embedding_model)

        _embedding_service = EmbeddingService(
            model=embedding_model,
            api_key=api_key,
            base_url=etl_config.get_openai_base_url(),  # Pass custom base URL
            dimension=etl_config.get_embedding_dimension()
        )

    return _embedding_service
