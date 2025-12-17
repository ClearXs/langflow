"""Shapefile Input Component.

Reads ESRI Shapefile format (.shp + supporting files) and converts to spatial data.
Supports .zip archives containing all required shapefile components.
"""

import i18n

from lfx.base.io.spatial_base import BaseSpatialInputComponent
from lfx.io import BoolInput, DropdownInput, FileInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data


class ShapefileInputComponent(BaseSpatialInputComponent):
    """Component for reading ESRI Shapefiles.

    Reads shapefiles from .zip archives containing .shp, .shx, .dbf, and optionally .prj files.
    Supports automatic encoding detection and CRS transformation.
    """

    display_name = i18n.t("components.spatial.shapefile_input.display_name")
    description = i18n.t("components.spatial.shapefile_input.description")
    icon = "Layers"
    name = "ShapefileInput"

    inputs = [
        FileInput(
            name="file_path",
            display_name=i18n.t("components.spatial.shapefile_input.file_path.display_name"),
            info=i18n.t("components.spatial.shapefile_input.file_path.info"),
            file_types=["zip", "shp"],
            temp_file=False,  # Trigger FileTableInputComponent
            required=False,  # Optional since file_id_variable can replace it
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.spatial.shapefile_input.file_id_variable.display_name"),
            info=i18n.t("components.spatial.shapefile_input.file_id_variable.info"),
            placeholder="{shapefileId}",
            required=False,  # Optional since file_path can replace it
            resolve_variables=True,  # Enable automatic variable resolution
        ),
        DropdownInput(
            name="target_crs",
            display_name=i18n.t("components.spatial.shapefile_input.target_crs.display_name"),
            info=i18n.t("components.spatial.shapefile_input.target_crs.info"),
            options=[
                "EPSG:4326",  # WGS84 (GPS coordinates)
                "EPSG:3857",  # Web Mercator (web maps)
                "EPSG:4490",  # CGCS2000 (China)
                "EPSG:2000",  # Aitoff (global projection)
                "custom",
            ],
            value="EPSG:4326",
            advanced=False,
        ),
        StrInput(
            name="encoding",
            display_name=i18n.t("components.spatial.shapefile_input.encoding.display_name"),
            info=i18n.t("components.spatial.shapefile_input.encoding.info"),
            value="utf-8",
            advanced=True,
        ),
        BoolInput(
            name="validate_geometry",
            display_name=i18n.t("components.spatial.shapefile_input.validate_geometry.display_name"),
            info=i18n.t("components.spatial.shapefile_input.validate_geometry.info"),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="fix_invalid",
            display_name=i18n.t("components.spatial.shapefile_input.fix_invalid.display_name"),
            info=i18n.t("components.spatial.shapefile_input.fix_invalid.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="spatial_data",
            display_name=i18n.t("components.spatial.shapefile_input.outputs.spatial_data.display_name"),
            method="load_shapefile",
        ),
    ]

    async def load_shapefile(self) -> list[Data]:
        """Load Shapefile and convert to Data objects.

        Returns:
            List of Data objects with spatial metadata

        Raises:
            ValueError: If file cannot be read or validation fails
            ImportError: If required spatial libraries not installed
        """
        try:
            import geopandas as gpd
        except ImportError as e:
            msg = i18n.t("components.spatial.shapefile_input.errors.missing_libraries")
            raise ImportError(msg) from e

        try:
            # Get file_id from either external variable or file selection
            file_id = self._get_file_id()

            # Download file if it's from resource management system
            file_path = await self._get_file_path(file_id)

            # Read Shapefile
            self.status = i18n.t("components.spatial.shapefile_input.status.reading_file")
            logger.info("Reading Shapefile: %s", file_path)

            # Handle .zip files containing shapefile components
            if file_path.endswith(".zip"):
                # GeoPandas can read directly from zip
                gdf = gpd.read_file(f"zip://{file_path}")
            else:
                # Direct .shp file
                gdf = gpd.read_file(file_path, encoding=self.encoding or "utf-8")

            if gdf.empty:
                msg = i18n.t("components.spatial.shapefile_input.errors.empty_file")
                raise ValueError(msg)

            # Detect and log CRS
            original_crs = str(gdf.crs) if gdf.crs else None
            if original_crs:
                logger.info("Detected CRS: %s", original_crs)
            else:
                logger.warning(i18n.t("components.spatial.shapefile_input.warnings.no_crs"))
                gdf.set_crs("EPSG:4326", inplace=True)

            # Transform CRS if needed
            if self.target_crs not in ("custom", original_crs):
                self.status = i18n.t(
                    "components.spatial.shapefile_input.status.transforming_crs", target_crs=self.target_crs
                )
                logger.info("Transforming CRS to %s", self.target_crs)
                gdf = gdf.to_crs(self.target_crs)

            # Validate geometry
            if self.validate_geometry:
                self.status = i18n.t("components.spatial.shapefile_input.status.validating_geometry")
                invalid_mask = ~gdf.geometry.is_valid

                if invalid_mask.any():
                    invalid_count = invalid_mask.sum()
                    logger.warning(
                        i18n.t("components.spatial.shapefile_input.warnings.invalid_geometries", count=invalid_count)
                    )

                    if self.fix_invalid:
                        # Attempt to fix invalid geometries
                        logger.info(i18n.t("components.spatial.shapefile_input.status.fixing_geometries"))
                        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)

                        # Check if fix worked
                        still_invalid = ~gdf.geometry.is_valid
                        if still_invalid.any():
                            remaining_count = still_invalid.sum()
                            logger.warning(
                                i18n.t(
                                    "components.spatial.shapefile_input.warnings.unfixed_geometries",
                                    count=remaining_count,
                                )
                            )
                    else:
                        msg = i18n.t("components.spatial.shapefile_input.errors.validation_failed", count=invalid_count)
                        raise ValueError(msg)

            # Convert to Data objects
            self.status = i18n.t("components.spatial.shapefile_input.status.converting_data")
            data_items = self._geodataframe_to_data(gdf)

            # Log success
            feature_count = len(data_items)
            geometry_types = gdf.geometry.geom_type.unique().tolist()
            self.status = i18n.t(
                "components.spatial.shapefile_input.success.loaded",
                count=feature_count,
                types=", ".join(geometry_types),
                crs=str(gdf.crs),
            )
            logger.info("Successfully loaded %d features with geometry types: %s", feature_count, geometry_types)

        except Exception as e:
            error_msg = i18n.t("components.spatial.shapefile_input.errors.loading_failed", error=str(e))
            self.status = error_msg
            logger.exception("Failed to load Shapefile")
            raise ValueError(error_msg) from e
        else:
            return data_items

    def _get_file_id(self) -> str:
        """Extract file_id from either file selection or external variable.

        Priority:
        1. file_id_variable (if provided and not empty)
        2. file_path (if provided)
        3. Raise error if neither provided

        Returns:
            str: File ID (resource ID from file browser or resolved variable)

        Raises:
            ValueError: If neither input is provided
        """
        # Priority 1: File Variable (with manual fallback if automatic resolution failed)
        if hasattr(self, "file_id_variable") and self.file_id_variable:
            variable_value = self.file_id_variable.strip()
            if variable_value:
                # Use base class helper method for variable resolution with fallback
                resolved_value = self._resolve_variable_with_fallback(
                    variable_value,
                    "components.spatial.shapefile_input.errors.variable_not_resolved"
                )
                logger.info(f"[ShapefileInput] Using file_id from variable: {resolved_value}")
                return resolved_value

        # Priority 2: File selection from UI - use existing extraction logic
        file_id = None

        # Check if _parameters has the original file_path structure
        if hasattr(self, "_parameters"):
            file_path_param = self._parameters.get("file_path")
            if isinstance(file_path_param, dict):
                file_id = file_path_param.get("file_path") or file_path_param.get("value")
                logger.info(f"[ShapefileInput] Extracted file_id from dict _parameters: {file_id}")
            elif isinstance(file_path_param, str):
                if file_path_param.isdigit():
                    file_id = file_path_param
                    logger.info(f"[ShapefileInput] Using numeric string from _parameters as file_id: {file_id}")
                else:
                    import os

                    basename = os.path.basename(file_path_param)
                    if basename.isdigit():
                        file_id = basename
                        logger.info(f"[ShapefileInput] Extracted file_id from cached path basename: {file_id}")
                    else:
                        file_id = file_path_param
                        logger.info(f"[ShapefileInput] Using path from _parameters: {file_id}")

        # Fallback to self.file_path
        if not file_id and hasattr(self, "file_path") and self.file_path:
            file_id = self.file_path
            logger.info(f"[ShapefileInput] Fallback to self.file_path: {file_id}")

        if file_id:
            logger.info(f"[ShapefileInput] Using file_id from file selection: {file_id}")
            return file_id

        # Neither provided - raise error
        error_msg = i18n.t("components.spatial.shapefile_input.errors.no_file_source")
        logger.error("[ShapefileInput] No file source provided")
        raise ValueError(error_msg)

    async def _get_file_path(self, file_id: str) -> str:
        """Get file path from file ID or direct path.

        Args:
            file_id: File ID from resource management or direct file path

        Returns:
            Absolute file path
        """
        # Check if it's a file ID (numeric) or direct path
        if str(file_id).isdigit():
            # Import download function
            from lfx.services.deps import get_file_service

            file_service = get_file_service()
            return await file_service.download_file(file_id)

        return file_id
