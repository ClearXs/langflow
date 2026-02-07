"""Chunking service for document processing.

Provides intelligent chunking strategies for different content types:
- RecursiveChunker: For general text (semantic-aware)
- CodeChunker: For code files (syntax-aware)
"""

import logging

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking documents into smaller pieces."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 128):
        """Initialize chunking service.

        Args:
            chunk_size: Target size for text chunks
            chunk_overlap: Overlap between chunks for context preservation
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize chunkers (lazy loading to avoid import errors)
        self._text_chunker = None
        self._code_chunker = None

    def _get_text_chunker(self):
        """Get or create text chunker (lazy loading)."""
        if self._text_chunker is None:
            try:
                from chonkie import RecursiveChunker

                self._text_chunker = RecursiveChunker(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
                logger.debug("Initialized RecursiveChunker")
            except ImportError:
                logger.warning("Chonkie not available, using fallback chunker")
                self._text_chunker = "fallback"

        return self._text_chunker

    def _get_code_chunker(self, language: str = "python"):
        """Get or create code chunker (lazy loading)."""
        if self._code_chunker is None:
            try:
                from chonkie import CodeChunker

                self._code_chunker = CodeChunker(
                    chunk_size=512,
                    chunk_overlap=64
                )
                logger.debug(f"Initialized CodeChunker for {language}")
            except ImportError:
                logger.warning("Chonkie CodeChunker not available, using fallback")
                self._code_chunker = "fallback"

        return self._code_chunker

    def _detect_language(self, file_type: str) -> str | None:
        """Detect programming language from file extension.

        Args:
            file_type: File extension (e.g., '.py', '.js')

        Returns:
            Language name or None
        """
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".cs": "csharp",
            ".sh": "bash",
            ".sql": "sql",
        }

        return ext_to_lang.get(file_type.lower())

    def _fallback_chunk(self, content: str, chunk_type: str = "text") -> list[dict]:
        """Fallback chunking when Chonkie is not available.

        Simple sliding window chunking.
        """
        chunks = []
        words = content.split()

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)

            if chunk_text.strip():
                chunks.append({
                    "content": chunk_text,
                    "type": chunk_type,
                    "index": len(chunks),
                    "language": None,
                    "token_count": len(chunk_words)
                })

        return chunks

    async def chunk_document(
        self,
        content: str,
        file_type: str | None = None,
        file_name: str | None = None
    ) -> list[dict]:
        """Chunk document content based on file type.

        Args:
            content: Document content to chunk
            file_type: File extension (e.g., '.pdf', '.py')
            file_name: Original filename (optional)

        Returns:
            List of chunk dictionaries with fields:
                - content: Chunk text
                - type: 'text' or 'code'
                - index: Position in document
                - language: Programming language (for code)
                - token_count: Estimated token count
        """
        if not content or not content.strip():
            logger.warning("Empty content provided to chunking service")
            return []

        # Detect if this is a code file
        code_extensions = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".java",
            ".cpp", ".c", ".h", ".hpp", ".go", ".rs",
            ".rb", ".php", ".swift", ".kt", ".scala",
            ".cs", ".sh", ".sql"
        }

        is_code = file_type and file_type.lower() in code_extensions
        language = self._detect_language(file_type) if is_code else None

        logger.info(
            f"Chunking document: type={file_type}, is_code={is_code}, "
            f"language={language}, length={len(content)}"
        )

        try:
            if is_code:
                # Use CodeChunker for code files
                chunker = self._get_code_chunker(language)

                if chunker == "fallback":
                    return self._fallback_chunk(content, chunk_type="code")

                chunks_obj = chunker.chunk(content)
                chunks = [
                    {
                        "content": chunk.text,
                        "type": "code",
                        "index": idx,
                        "language": language,
                        "token_count": len(chunk.text.split())
                    }
                    for idx, chunk in enumerate(chunks_obj)
                ]

            else:
                # Use RecursiveChunker for text files
                chunker = self._get_text_chunker()

                if chunker == "fallback":
                    return self._fallback_chunk(content, chunk_type="text")

                chunks_obj = chunker.chunk(content)
                chunks = [
                    {
                        "content": chunk.text,
                        "type": "text",
                        "index": idx,
                        "language": None,
                        "token_count": len(chunk.text.split())
                    }
                    for idx, chunk in enumerate(chunks_obj)
                ]

            logger.info(f"Created {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Chunking failed: {e}, using fallback")
            return self._fallback_chunk(content, chunk_type="code" if is_code else "text")


# Global instance
_chunking_service = None


def get_chunking_service() -> ChunkingService:
    """Get or create global chunking service instance."""
    global _chunking_service

    if _chunking_service is None:
        from langflow.services.etl.config import etl_config

        _chunking_service = ChunkingService(
            chunk_size=etl_config.chunk_size,
            chunk_overlap=etl_config.chunk_overlap
        )

    return _chunking_service
