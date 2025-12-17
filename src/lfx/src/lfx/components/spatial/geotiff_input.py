"""GeoTIFF Input Component.

Reads GeoTIFF raster files and converts to spatial data with metadata.
Supports multiple GeoTIFF files and various read modes.
"""

from typing import Any

import i18n

from lfx.base.io.spatial_base import BaseSpatialInputComponent
from lfx.io import BoolInput, DropdownInput, FileInput, IntInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema import Data


class GeoTIFFInputComponent(BaseSpatialInputComponent):
    """Component for reading GeoTIFF raster files.

    Reads GeoTIFF files and extracts raster data with spatial metadata including
    CRS, bounds, resolution, and band information.
    """

    display_name = i18n.t("components.spatial.geotiff_input.display_name")
    description = i18n.t("components.spatial.geotiff_input.description")
    icon = "Image"
    name = "GeoTIFFInput"

    inputs = [
        FileInput(
            name="file_path",
            display_name=i18n.t("components.spatial.geotiff_input.file_path.display_name"),
            info=i18n.t("components.spatial.geotiff_input.file_path.info"),
            file_types=["tif", "tiff"],
            is_list=True,
            temp_file=False,  # Trigger FileTableInputComponent
            required=False,  # Optional since file_id_variable can replace it
        ),
        StrInput(
            name="file_id_variable",
            display_name=i18n.t("components.spatial.geotiff_input.file_id_variable.display_name"),
            info=i18n.t("components.spatial.geotiff_input.file_id_variable.info"),
            placeholder="{geoTiffFileId}",
            required=False,  # Optional since file_path can replace it
            resolve_variables=True,  # Enable automatic variable resolution
        ),
        DropdownInput(
            name="read_mode",
            display_name=i18n.t("components.spatial.geotiff_input.read_mode.display_name"),
            info=i18n.t("components.spatial.geotiff_input.read_mode.info"),
            options=[
                "metadata",  # Only metadata
                "array",  # Full array data
                "sample",  # Sampled points
            ],
            value="metadata",
            advanced=False,
        ),
        IntInput(
            name="sample_size",
            display_name=i18n.t("components.spatial.geotiff_input.sample_size.display_name"),
            info=i18n.t("components.spatial.geotiff_input.sample_size.info"),
            value=1000,
            advanced=True,
        ),
        BoolInput(
            name="merge_files",
            display_name=i18n.t("components.spatial.geotiff_input.merge_files.display_name"),
            info=i18n.t("components.spatial.geotiff_input.merge_files.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="spatial_data",
            display_name=i18n.t("components.spatial.geotiff_input.outputs.spatial_data.display_name"),
            method="load_geotiff",
        ),
    ]

    async def load_geotiff(self) -> list[Data]:
        """Load GeoTIFF file(s) and convert to Data objects.

        Returns:
            List of Data objects with raster metadata

        Raises:
            ValueError: If file cannot be read
            ImportError: If required spatial libraries not installed
        """
        try:
            import rasterio
            from rasterio.merge import merge
        except ImportError as e:
            msg = i18n.t("components.spatial.geotiff_input.errors.missing_libraries")
            raise ImportError(msg) from e

        try:
            # Get file_ids from either external variable or file selection
            file_paths = self._get_file_id()

            # Download files if needed
            downloaded_paths = []
            for file_id in file_paths:
                file_path = await self._get_file_path(file_id)
                downloaded_paths.append(file_path)

            self.status = i18n.t("components.spatial.geotiff_input.status.reading_files", count=len(downloaded_paths))
            logger.info("Reading %d GeoTIFF file(s)", len(downloaded_paths))

            # Open all raster datasets
            datasets = []
            for path in downloaded_paths:
                try:
                    ds = rasterio.open(path)
                    datasets.append(ds)
                except (OSError, ValueError) as e:
                    logger.warning("Failed to open raster file %s: %s", path, e)
                    continue

            if not datasets:
                msg = i18n.t("components.spatial.geotiff_input.errors.no_valid_files")
                raise ValueError(msg)

            # Merge or process individually
            data_items = []

            if self.merge_files and len(datasets) > 1:
                self.status = i18n.t("components.spatial.geotiff_input.status.merging_files")
                logger.info("Merging %d raster files", len(datasets))

                # Merge datasets
                mosaic, transform = merge(datasets)

                # Create merged metadata
                merged_data = self._create_raster_data(datasets[0], mosaic, transform, "merged")
                data_items.append(merged_data)

            else:
                # Process each raster individually
                for idx, ds in enumerate(datasets):
                    self.status = i18n.t(
                        "components.spatial.geotiff_input.status.processing_file",
                        current=idx + 1,
                        total=len(datasets),
                    )

                    raster_data = self._create_raster_data(ds, None, None, downloaded_paths[idx])
                    data_items.append(raster_data)

            # Close all datasets
            for ds in datasets:
                ds.close()

            # Log success
            self.status = i18n.t("components.spatial.geotiff_input.success.loaded", count=len(data_items))
            logger.info("Successfully loaded %d raster dataset(s)", len(data_items))

        except Exception as e:
            error_msg = i18n.t("components.spatial.geotiff_input.errors.loading_failed", error=str(e))
            self.status = error_msg
            logger.exception("Failed to load GeoTIFF")
            raise ValueError(error_msg) from e
        else:
            return data_items

    def _create_raster_data(self, dataset: Any, array_data: Any, transform: Any, source_name: str) -> Data:
        """Create Data object from raster dataset.

        Args:
            dataset: Rasterio dataset
            array_data: Optional array data (if read_mode is 'array')
            transform: Optional transform (for merged data)
            source_name: Name/path of the source file

        Returns:
            Data object with raster metadata
        """
        import numpy as np

        # Base metadata
        metadata = {
            "source": source_name,
            "crs": str(dataset.crs) if dataset.crs else "EPSG:4326",
            "width": dataset.width,
            "height": dataset.height,
            "count": dataset.count,
            "dtype": str(dataset.dtypes[0]),
            "bounds": {
                "minx": dataset.bounds.left,
                "miny": dataset.bounds.bottom,
                "maxx": dataset.bounds.right,
                "maxy": dataset.bounds.top,
            },
            "transform": list(dataset.transform)[:6] if not transform else list(transform)[:6],
            "resolution": {
                "x": dataset.res[0],
                "y": dataset.res[1],
            },
        }

        # Add nodata value if present
        if dataset.nodata is not None:
            metadata["nodata"] = float(dataset.nodata)

        # Read data based on mode
        if self.read_mode == "array" and array_data is not None:
            # Use provided array data (merged)
            metadata["array_shape"] = list(array_data.shape)
            metadata["array_data"] = array_data.tolist() if array_data.size < 10000 else "Array too large to serialize"  # noqa: PLR2004

        elif self.read_mode == "array":
            # Read full array
            array = dataset.read()
            metadata["array_shape"] = list(array.shape)
            metadata["array_data"] = array.tolist() if array.size < 10000 else "Array too large to serialize"  # noqa: PLR2004

        elif self.read_mode == "sample":
            # Sample random points
            self.status = i18n.t("components.spatial.geotiff_input.status.sampling_points")

            # Generate random sample points using modern numpy API
            sample_size = min(self.sample_size, dataset.width * dataset.height)
            rng = np.random.default_rng()
            rows = rng.integers(0, dataset.height, size=sample_size)
            cols = rng.integers(0, dataset.width, size=sample_size)

            # Read sample values
            band_data = dataset.read(1)
            sample_values = [float(band_data[r, c]) for r, c in zip(rows, cols, strict=False)]

            metadata["sample_points"] = {
                "count": sample_size,
                "values": sample_values[:100],  # Limit to 100 values in output
                "statistics": {
                    "min": float(np.min(sample_values)),
                    "max": float(np.max(sample_values)),
                    "mean": float(np.mean(sample_values)),
                    "std": float(np.std(sample_values)),
                },
            }

        # Create Data object
        return Data(data=metadata)

    def _get_file_id(self) -> list[str]:
        """Extract file_id(s) from either file selection or external variable.

        Priority:
        1. file_id_variable (if provided and not empty)
        2. file_path (if provided)
        3. Raise error if neither provided

        Returns:
            list[str]: List of file IDs (resource IDs from file browser or resolved variable)

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
                    "components.spatial.geotiff_input.errors.variable_not_resolved"
                )
                logger.info(f"[GeoTIFFInput] Using file_id from variable: {resolved_value}")
                # Support comma-separated list for multiple files
                return [v.strip() for v in resolved_value.split(",") if v.strip()]

        # Priority 2: File selection from UI - use existing extraction logic
        file_ids = []

        # Check if _parameters has the original file_path structure
        if hasattr(self, "_parameters"):
            file_path_param = self._parameters.get("file_path")
            if isinstance(file_path_param, list):
                # List of file IDs or paths
                for item in file_path_param:
                    if isinstance(item, dict):
                        file_id = item.get("file_path") or item.get("value")
                        if file_id:
                            file_ids.append(file_id)
                    elif isinstance(item, str):
                        file_ids.append(item)
                logger.info(f"[GeoTIFFInput] Extracted file_ids from list _parameters: {file_ids}")
            elif isinstance(file_path_param, dict):
                file_id = file_path_param.get("file_path") or file_path_param.get("value")
                if file_id:
                    file_ids.append(file_id)
                logger.info(f"[GeoTIFFInput] Extracted file_id from dict _parameters: {file_ids}")
            elif isinstance(file_path_param, str):
                file_ids.append(file_path_param)
                logger.info(f"[GeoTIFFInput] Using string from _parameters as file_id: {file_ids}")

        # Fallback to self.file_path
        if not file_ids and hasattr(self, "file_path") and self.file_path:
            if isinstance(self.file_path, list):
                file_ids = self.file_path
            else:
                file_ids = [self.file_path]
            logger.info(f"[GeoTIFFInput] Fallback to self.file_path: {file_ids}")

        if file_ids:
            logger.info(f"[GeoTIFFInput] Using file_ids from file selection: {file_ids}")
            return file_ids

        # Neither provided - raise error
        error_msg = i18n.t("components.spatial.geotiff_input.errors.no_file_source")
        logger.error("[GeoTIFFInput] No file source provided")
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
