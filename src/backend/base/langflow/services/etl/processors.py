"""ETL Processors for document parsing.

Supports multiple ETL services:
- Unstructured API: Universal document parser with cloud API
- LlamaCloud: High-quality PDF and document parsing
- Docling: Fast local processing
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class ETLProcessor(ABC):
    """Base class for ETL processors."""

    @abstractmethod
    async def process(self, file_path: str) -> str:
        """Process a file and return markdown content.

        Args:
            file_path: Path to the file to process

        Returns:
            Markdown-formatted content
        """

    @abstractmethod
    def supports_file_type(self, file_extension: str) -> bool:
        """Check if processor supports this file type."""


class UnstructuredETLProcessor(ETLProcessor):
    """ETL processor using Unstructured API."""

    def __init__(self, api_key: str, api_url: str, strategy: str = "auto", mode: str = "elements"):
        """Initialize Unstructured processor.

        Args:
            api_key: Unstructured API key
            api_url: API endpoint URL
            strategy: Parsing strategy (auto, fast, hi_res)
            mode: Output mode (elements, paged)
        """
        self.api_key = api_key
        self.api_url = api_url
        self.strategy = strategy
        self.mode = mode

    def supports_file_type(self, file_extension: str) -> bool:
        """Unstructured supports most common document formats."""
        supported = {
            ".pdf", ".docx", ".doc", ".pptx", ".ppt",
            ".xlsx", ".xls", ".csv", ".txt", ".md",
            ".html", ".xml", ".json", ".eml", ".msg"
        }
        return file_extension.lower() in supported

    async def process(self, file_path: str) -> str:
        """Process file using Unstructured API.

        This uses the partition API which automatically detects
        document type and extracts structured elements.
        """
        try:
            from langchain_unstructured import UnstructuredLoader

            logger.info(f"Processing {file_path} with Unstructured API")

            loader = UnstructuredLoader(
                file_path,
                mode=self.mode,
                strategy=self.strategy,
                api_key=self.api_key,
                url=self.api_url
            )

            # Load documents
            docs = await loader.aload()

            # Convert to markdown
            markdown_parts = []
            for doc in docs:
                category = doc.metadata.get("category", "")

                if category == "Title":
                    markdown_parts.append(f"# {doc.page_content}\n")
                elif category == "Header":
                    markdown_parts.append(f"## {doc.page_content}\n")
                elif category == "NarrativeText":
                    markdown_parts.append(f"{doc.page_content}\n\n")
                elif category == "ListItem":
                    markdown_parts.append(f"- {doc.page_content}\n")
                elif category == "Table":
                    markdown_parts.append(f"```table\n{doc.page_content}\n```\n\n")
                elif category == "Code":
                    lang = doc.metadata.get("language", "")
                    markdown_parts.append(f"```{lang}\n{doc.page_content}\n```\n\n")
                else:
                    markdown_parts.append(f"{doc.page_content}\n\n")

            result = "".join(markdown_parts)
            logger.info(f"Unstructured API processed {len(docs)} elements")
            return result

        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            raise


class LlamaCloudETLProcessor(ETLProcessor):
    """ETL processor using LlamaCloud/LlamaParse."""

    def __init__(self, api_key: str, result_type: str = "markdown"):
        """Initialize LlamaCloud processor.

        Args:
            api_key: LlamaCloud API key
            result_type: Output format (markdown, text)
        """
        self.api_key = api_key
        self.result_type = result_type

    def supports_file_type(self, file_extension: str) -> bool:
        """LlamaCloud is optimized for PDF and Office documents."""
        supported = {
            ".pdf", ".docx", ".doc", ".pptx", ".ppt",
            ".xlsx", ".xls"
        }
        return file_extension.lower() in supported

    async def process(self, file_path: str) -> str:
        """Process file using LlamaCloud.

        LlamaCloud excels at PDF parsing with complex layouts.
        """
        try:
            from llama_parse import LlamaParse

            logger.info(f"Processing {file_path} with LlamaCloud")

            parser = LlamaParse(
                api_key=self.api_key,
                result_type=self.result_type,
                verbose=True
            )

            # Parse document
            result = await parser.aparse(file_path)

            # Extract markdown documents
            if self.result_type == "markdown":
                markdown_docs = await result.aget_markdown_documents()
                content = "\n\n".join([doc.text for doc in markdown_docs])
            else:
                content = result.text

            logger.info("LlamaCloud processed document successfully")
            return content

        except Exception as e:
            logger.error(f"LlamaCloud processing failed: {e}")
            raise


class DoclingETLProcessor(ETLProcessor):
    """ETL processor using Docling (local processing)."""

    def __init__(self, batch_size: int = 10):
        """Initialize Docling processor.

        Args:
            batch_size: Number of pages to process in each batch
        """
        self.batch_size = batch_size

    def supports_file_type(self, file_extension: str) -> bool:
        """Docling supports common document formats."""
        supported = {
            ".pdf", ".docx", ".doc", ".pptx", ".txt", ".md"
        }
        return file_extension.lower() in supported

    async def process(self, file_path: str) -> str:
        """Process file using Docling.

        Docling provides fast local processing without API calls.
        Uses batch processing to avoid memory issues.
        """
        try:
            logger.info(f"Processing {file_path} with Docling (local)")

            # Basic text extraction for simple formats
            file_ext = Path(file_path).suffix.lower()

            if file_ext in [".txt", ".md"]:
                # Direct text file reading
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return content

            if file_ext == ".pdf":
                # PDF extraction using PyPDF2 or similar
                try:
                    import PyPDF2

                    markdown_parts = []
                    with open(file_path, "rb") as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        total_pages = len(pdf_reader.pages)

                        logger.info(f"Processing {total_pages} pages")

                        # Process in batches
                        for i in range(0, total_pages, self.batch_size):
                            batch_end = min(i + self.batch_size, total_pages)

                            for page_num in range(i, batch_end):
                                page = pdf_reader.pages[page_num]
                                text = page.extract_text()
                                if text.strip():
                                    markdown_parts.append(f"## Page {page_num + 1}\n\n{text}\n\n")

                    return "".join(markdown_parts)

                except ImportError:
                    logger.warning("PyPDF2 not available, using basic extraction")
                    return await self._basic_extraction(file_path)

            elif file_ext in [".docx"]:
                # DOCX extraction
                try:
                    import docx

                    doc = docx.Document(file_path)
                    markdown_parts = []

                    for para in doc.paragraphs:
                        text = para.text.strip()
                        if text:
                            # Detect headings by style
                            if para.style.name.startswith("Heading"):
                                level = para.style.name[-1] if para.style.name[-1].isdigit() else "1"
                                markdown_parts.append(f"{'#' * int(level)} {text}\n\n")
                            else:
                                markdown_parts.append(f"{text}\n\n")

                    return "".join(markdown_parts)

                except ImportError:
                    logger.warning("python-docx not available, using basic extraction")
                    return await self._basic_extraction(file_path)

            else:
                # Fallback to basic extraction
                return await self._basic_extraction(file_path)

        except Exception as e:
            logger.error(f"Docling processing failed: {e}")
            raise

    async def _basic_extraction(self, file_path: str) -> str:
        """Fallback: basic text extraction."""
        with open(file_path, "rb") as f:
            content = f.read()

        # Try UTF-8 decoding
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return f"File: {Path(file_path).name}\nBinary content ({len(content)} bytes)"


def get_etl_processor(service: str | None = None) -> ETLProcessor:
    """Factory function to get ETL processor based on configuration.

    Args:
        service: Service name (unstructured, llamacloud, docling) or None to use config

    Returns:
        ETL processor instance

    Raises:
        ValueError: If service is not configured or unsupported
    """
    from langflow.services.etl.config import etl_config

    service_name = service or etl_config.etl_service

    if service_name == "unstructured":
        api_key = etl_config.get_api_key("unstructured")
        if not api_key:
            raise ValueError("Unstructured API key not configured")

        return UnstructuredETLProcessor(
            api_key=api_key,
            api_url=etl_config.unstructured_api_url,
            strategy=etl_config.unstructured_strategy,
            mode=etl_config.unstructured_mode
        )

    if service_name == "llamacloud":
        api_key = etl_config.get_api_key("llamacloud")
        if not api_key:
            raise ValueError("LlamaCloud API key not configured")

        return LlamaCloudETLProcessor(
            api_key=api_key,
            result_type=etl_config.llama_cloud_result_type
        )

    if service_name == "docling":
        if not etl_config.docling_enabled:
            raise ValueError("Docling is not enabled")

        return DoclingETLProcessor(
            batch_size=etl_config.docling_batch_size
        )

    raise ValueError(f"Unsupported ETL service: {service_name}")


async def process_document_with_fallback(file_path: str) -> tuple[str, str]:
    """Process document with automatic fallback to secondary service.

    Args:
        file_path: Path to file

    Returns:
        Tuple of (markdown_content, service_used)
    """
    from langflow.services.etl.config import etl_config

    # Try primary service
    try:
        processor = get_etl_processor(etl_config.etl_service)
        content = await processor.process(file_path)
        return content, etl_config.etl_service

    except Exception as e:
        logger.warning(f"Primary ETL service failed: {e}, falling back to {etl_config.etl_fallback_service}")

        # Try fallback service
        try:
            processor = get_etl_processor(etl_config.etl_fallback_service)
            content = await processor.process(file_path)
            return content, etl_config.etl_fallback_service

        except Exception as fallback_error:
            logger.error(f"Fallback ETL service also failed: {fallback_error}")
            raise RuntimeError(
                f"All ETL services failed. Primary: {e}, Fallback: {fallback_error}"
            ) from fallback_error
