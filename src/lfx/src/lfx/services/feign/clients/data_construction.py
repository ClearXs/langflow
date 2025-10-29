"""Data construction service Feign client."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class DataConstructionFeignClient:
    """Data construction service Feign client."""

    SERVICE_NAME = "data-construction"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def download_file(self, file_id: int) -> tuple[bytes, str]:
        """Download file.

        Args:
            file_id: Resource file ID

        Returns:
            (file_content, filename) tuple

        Raises:
            ValueError: Download failed
        """
        try:
            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path=f"/resource-file/download/{file_id}",
            )

            # Extract filename from Content-Disposition header
            content_disposition = response.headers.get("content-disposition", "")
            filename = None

            if content_disposition:
                parts = content_disposition.split("filename=")
                if len(parts) > 1:
                    filename = parts[1].strip('"').strip("'")
                    try:
                        from urllib.parse import unquote

                        filename = unquote(filename)
                    except (ValueError, TypeError):
                        # Keep original filename if unquote fails
                        pass

            if not filename:
                filename = f"file_{file_id}"

            logger.info(
                f"[DataConstructionClient] Downloaded file {file_id}: {filename} ({len(response.content)} bytes)"
            )

        except Exception as e:
            error_msg = f"Failed to download file {file_id}: {e}"
            logger.exception(f"[DataConstructionClient] {error_msg}")
            raise ValueError(error_msg) from e
        else:
            return response.content, filename

    async def get_file_detail(self, file_id: int) -> dict:
        """Get file detail.

        Args:
            file_id: Resource file ID

        Returns:
            File detail dictionary
        """
        response = await self.feign_service.get(
            service_name=self.SERVICE_NAME,
            path="/resource-file/detail",
            params={"id": file_id},
        )
        return response.json()

    async def get_datasource_list(self) -> list[dict]:
        """Get datasource list from feign API.

        Returns:
            List of datasource dictionaries

        Raises:
            ValueError: Failed to get datasource list
        """
        try:
            logger.info(f"[DataConstructionClient] Attempting to get datasource list from service: {self.SERVICE_NAME}")

            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path="/feign/client/data-construction/datasource-manage/getDatasourceList",
            )

            # Parse response data
            response_data = response.json()
            logger.debug(f"[DataConstructionClient] Raw response data: {response_data}")

            # Handle R<List<DatasourceManageVO>> response structure
            if isinstance(response_data, dict):
                if "data" in response_data:
                    datasource_list = response_data["data"]
                    logger.info(f"[DataConstructionClient] Got {len(datasource_list)} datasources from feign API")
                    return datasource_list if isinstance(datasource_list, list) else []
                # If no data field, return the whole response if it's a list
                if isinstance(response_data, list):
                    logger.info(f"[DataConstructionClient] Got {len(response_data)} datasources from feign API")
                    return response_data
                logger.warning(f"[DataConstructionClient] Unexpected response format: {response_data}")
                return []
            if isinstance(response_data, list):
                logger.info(f"[DataConstructionClient] Got {len(response_data)} datasources from feign API")
                return response_data
            logger.warning(f"[DataConstructionClient] Unexpected response type: {type(response_data)}")
            return []

        except ValueError as e:
            # 特殊处理Nacos服务未找到的情况
            if "No healthy instances found" in str(e):
                logger.warning(f"[DataConstructionClient] Service {self.SERVICE_NAME} not found in Nacos. This might be normal if the service is not deployed.")
                return []
            error_msg = f"Failed to get datasource list: {e}"
            logger.exception(f"[DataConstructionClient] {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to get datasource list: {e}"
            logger.exception(f"[DataConstructionClient] {error_msg}")
            raise ValueError(error_msg) from e

    async def get_datasource_detail(self, datasource_id: int) -> dict:
        """Get datasource detail by ID.

        Args:
            datasource_id: Datasource ID

        Returns:
            Datasource detail dictionary

        Raises:
            ValueError: Failed to get datasource detail
        """
        try:
            response = await self.feign_service.get(
                service_name=self.SERVICE_NAME,
                path="/feign/client/data-construction/datasource-manage/getDatasourceManageById",
                params={"id": datasource_id},
            )

            response_data = response.json()

            # Handle R<DatasourceManageVO> response structure
            if isinstance(response_data, dict) and "data" in response_data:
                datasource_detail = response_data["data"]
                logger.info(f"[DataConstructionClient] Got datasource detail for ID {datasource_id}")
                return datasource_detail
            logger.info(f"[DataConstructionClient] Got datasource detail for ID {datasource_id}")
            return response_data

        except Exception as e:
            error_msg = f"Failed to get datasource detail {datasource_id}: {e}"
            logger.exception(f"[DataConstructionClient] {error_msg}")
            raise ValueError(error_msg) from e


# ============= Convenience Functions =============


async def download_file_by_id(file_id: str | int) -> str:
    """Download file to temporary directory.

    Args:
        file_id: File ID

    Returns:
        Temporary file path

    Raises:
        ValueError: Download failed

    Example:
        temp_path = await download_file_by_id(file_id="123")
        try:
            df = pd.read_csv(temp_path)
        finally:
            cleanup_temp_file(temp_path)
    """
    from lfx.services.deps import get_feign_service

    feign_service = get_feign_service()
    client = DataConstructionFeignClient(feign_service)

    # Download file
    content, filename = await client.download_file(int(file_id))

    # Save to temporary file
    suffix = Path(filename).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=suffix,
        delete=False,
        prefix=f"lfx_feign_{file_id}_",
    ) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        temp_path = temp_file.name

    logger.info(f"[DataConstructionClient] Saved to temp file: {temp_path}")
    return temp_path


def cleanup_temp_file(file_path: str) -> None:
    """Cleanup temporary file.

    Args:
        file_path: Temporary file path
    """
    try:
        if file_path and Path(file_path).exists():
            Path(file_path).unlink()
            logger.info(f"[DataConstructionClient] Cleaned up: {file_path}")
    except (OSError, PermissionError) as e:
        logger.warning(f"[DataConstructionClient] Cleanup failed: {file_path}, {e}")


async def upload_file_to_folder(folder_id: int, file_path: str, filename: str | None = None) -> dict:
    """Upload file to resource management system.

    Args:
        folder_id: Target folder ID
        file_path: Local temporary file path
        filename: Desired filename (optional, uses file_path basename if not provided)

    Returns:
        dict: Uploaded file info from response.data

    Raises:
        ValueError: Upload failed with error message from API

    Example:
        result = await upload_file_to_folder(
            folder_id=123,
            file_path="/tmp/data.csv",
            filename="sales_report.csv"
        )
        # Returns: {"id": 456, "name": "sales_report.csv", ...}
    """
    from lfx.services.deps import get_feign_service

    if filename is None:
        filename = Path(file_path).name

    logger.info(f"[DataConstructionClient] Uploading {filename} to folder {folder_id}")

    try:
        feign_service = get_feign_service()

        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()

        logger.info(f"[DataConstructionClient] File size: {len(file_content)} bytes")

        # Prepare multipart upload
        files = {"file": (filename, file_content, "application/octet-stream")}

        # Upload via POST
        response = await feign_service.post_multipart(
            service_name="data-construction",
            path="/resource-file/put-file",
            params={"folderId": folder_id},
            files=files,
        )

        # Parse R<T> response structure
        response_data = response.json()

        # Check response structure
        if not isinstance(response_data, dict):
            msg = f"Invalid response format: {response_data}"
            raise ValueError(msg)

        success = response_data.get("success", False)
        code = response_data.get("code")
        msg = response_data.get("msg", "Unknown error")
        data = response_data.get("data")

        # Handle error response
        if not success:
            error_msg = f"Upload failed (code={code}): {msg}"
            logger.error(f"[DataConstructionClient] {error_msg}")
            raise ValueError(error_msg)

        if data is None:
            logger.warning(f"[DataConstructionClient] Upload succeeded but data is null: {msg}")
            # Return minimal info if data is null
            return {"id": None, "name": filename, "msg": msg}

        logger.info(f"[DataConstructionClient] Upload successful: file_id={data.get('id')}, msg={msg}")

        return data

    except Exception as e:
        # If it's already a ValueError from error response, re-raise it
        if isinstance(e, ValueError):
            raise

        # Handle other exceptions
        import httpx

        if isinstance(e, httpx.HTTPStatusError):
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
        else:
            error_msg = f"Upload error: {e}"

        logger.exception(f"[DataConstructionClient] {error_msg}")
        raise ValueError(error_msg) from e
