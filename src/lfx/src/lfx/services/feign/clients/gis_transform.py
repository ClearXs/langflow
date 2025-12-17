"""GIS transform service Feign client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lfx.log.logger import logger

if TYPE_CHECKING:
    from lfx.services.feign.service import FeignService


class GISTransformFeignClient:
    """GIS transform service Feign client for geo-spatial data processing."""

    SERVICE_NAME = "computing-service"

    def __init__(self, feign_service: FeignService):
        """Initialize client.

        Args:
            feign_service: Feign service instance
        """
        self.feign_service = feign_service

    async def encode_geo_entity(
        self,
        geometry: dict,
        entity_class_name: str,
        level: int = 8,
    ) -> str | None:
        """Encode geographic entity with spatial classification code.

        Args:
            geometry: GeoJSON geometry object with structure:
                {
                    "type": "Point",
                    "coordinates": [114.26101, 30.58392]
                }
            entity_class_name: Entity classification name (e.g., "山峰", "河流")
            level: Encoding level (1-20), default is 8

        Returns:
            Encoded spatial entity classification string, or None if failed

        Raises:
            ValueError: If encoding fails
        """
        try:
            logger.info(
                f"[GISTransformClient] Encoding geo entity '{entity_class_name}' at level {level}"
            )

            request_body = {
                "geometry": geometry,
                "entityClassName": entity_class_name,
                "level": level,
            }

            response = await self.feign_service.post(
                service_name=self.SERVICE_NAME,
                path="/geo-entity/encode",
                json=request_body,
            )

            response_data = response.json()
            logger.debug(f"[GISTransformClient] Geo entity encode response: {response_data}")

            # Handle R<String> response structure
            if isinstance(response_data, dict):
                if "data" in response_data:
                    encoded_value = response_data["data"]
                    logger.info(
                        f"[GISTransformClient] Successfully encoded geo entity: {encoded_value}"
                    )
                    return encoded_value
                if "success" in response_data and not response_data["success"]:
                    error_msg = response_data.get("msg", "Encoding failed")
                    logger.warning(f"[GISTransformClient] Encoding failed: {error_msg}")
                    return None

            # If response is directly a string
            if isinstance(response_data, str):
                logger.info(f"[GISTransformClient] Successfully encoded geo entity: {response_data}")
                return response_data

            logger.warning(f"[GISTransformClient] Unexpected response format: {response_data}")
            return None

        except ValueError as e:
            # Special handling for Nacos service not found
            if "No healthy instances found" in str(e):
                logger.warning(
                    f"[GISTransformClient] Service {self.SERVICE_NAME} not found in Nacos. "
                    "This might be normal if the service is not deployed."
                )
                return None
            error_msg = f"Failed to encode geo entity: {e}"
            logger.exception(f"[GISTransformClient] {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to encode geo entity: {e}"
            logger.exception(f"[GISTransformClient] {error_msg}")
            raise ValueError(error_msg) from e

    async def transform_coordinate(
        self,
        x: float,
        y: float,
        z: float | None = None,
        source_crs: str = "EPSG:4326",
        target_crs: str = "EPSG:3857",
    ) -> list[float]:
        """Transform coordinates between coordinate reference systems.

        Uses the universal coordinate transformation API that supports all CRS conversions.

        Args:
            x: X coordinate (longitude for geographic CRS, easting for projected CRS)
            y: Y coordinate (latitude for geographic CRS, northing for projected CRS)
            z: Optional Z coordinate (elevation/height)
            source_crs: Source CRS identifier (e.g., "EPSG:4326", "EPSG:3857")
            target_crs: Target CRS identifier (e.g., "EPSG:4326", "EPSG:3857")

        Returns:
            Transformed coordinates as [x, y] or [x, y, z] list

        Raises:
            ValueError: If transformation fails
        """
        try:
            logger.info(
                f"[GISTransformClient] Transforming coordinates ({x}, {y}{f', {z}' if z is not None else ''}) "
                f"from {source_crs} to {target_crs}"
            )

            request_body = {
                "x": x,
                "y": y,
                "sourceCrs": source_crs,
                "targetCrs": target_crs,
            }

            # Add Z coordinate if provided
            if z is not None:
                request_body["z"] = z

            response = await self.feign_service.post(
                service_name=self.SERVICE_NAME,
                path="/coordinate-conversion/transform",
                json=request_body,
            )

            response_data = response.json()
            logger.debug(f"[GISTransformClient] Transform response: {response_data}")

            # Handle R<double[]> response structure
            if isinstance(response_data, dict):
                if "data" in response_data:
                    transformed = response_data["data"]
                    if isinstance(transformed, list):
                        logger.info(
                            f"[GISTransformClient] Successfully transformed coordinates: {transformed}"
                        )
                        return transformed
                    logger.warning(
                        f"[GISTransformClient] Expected list in response data, got {type(transformed)}: {transformed}"
                    )
                    return [x, y] if z is None else [x, y, z]  # Return original on unexpected format

                if "success" in response_data and not response_data["success"]:
                    error_msg = response_data.get("msg", "Transformation failed")
                    raise ValueError(f"Coordinate transformation failed: {error_msg}")

            # If response is directly a list
            if isinstance(response_data, list):
                logger.info(
                    f"[GISTransformClient] Successfully transformed coordinates: {response_data}"
                )
                return response_data

            logger.warning(f"[GISTransformClient] Unexpected response format: {response_data}")
            return [x, y] if z is None else [x, y, z]  # Return original on unexpected format

        except ValueError as e:
            # Special handling for Nacos service not found
            if "No healthy instances found" in str(e):
                error_msg = f"Service {self.SERVICE_NAME} not available for coordinate transformation"
                logger.error(f"[GISTransformClient] {error_msg}")
                raise ValueError(error_msg) from e
            error_msg = f"Failed to transform coordinates: {e}"
            logger.exception(f"[GISTransformClient] {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to transform coordinates: {e}"
            logger.exception(f"[GISTransformClient] {error_msg}")
            raise ValueError(error_msg) from e


# ============= Convenience Functions =============


def get_gis_transform_client(feign_service: FeignService) -> GISTransformFeignClient:
    """Get GIS transform Feign client.

    Args:
        feign_service: Feign service instance

    Returns:
        GISTransformFeignClient instance
    """
    return GISTransformFeignClient(feign_service)
