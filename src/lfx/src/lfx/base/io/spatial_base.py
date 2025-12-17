"""Base classes for spatial data components.

This module provides base classes for spatial input/output components that handle
geographic data (GeoJSON, Shapefile, GeoTIFF, etc.). It extends the existing
BaseTableInputComponent and BaseTableOutputComponent with spatial-specific functionality.

Key Features:
- GeoDataFrame ↔ Data object conversion
- Spatial metadata handling (CRS, geometry type, bounds)
- Geometry serialization (GeoJSON format)
- Coordinate reference system (CRS) management
"""

import logging
from typing import Any

import pandas as pd

from lfx.base.io.table_base import BaseTableInputComponent, BaseTableOutputComponent
from lfx.schema import Data

logger = logging.getLogger(__name__)


class BaseSpatialInputComponent(BaseTableInputComponent):
    """Base class for spatial input components.

    Extends BaseTableInputComponent to support geographic data formats.
    Handles conversion from GeoDataFrame to Data objects with spatial metadata.

    Spatial Metadata Keys:
        geometry: Geometry in GeoJSON format (standard field name)
        _geometry_type: Type of geometry (Point, LineString, Polygon, etc.)
        _crs: Coordinate reference system (e.g., EPSG:4326)
    """

    def _build_connection_string(self) -> str:
        """Build connection string for spatial data source.

        Spatial components don't use traditional database connections,
        so this returns an empty string.
        """
        return ""

    def _load_tables(self) -> list[str]:
        """Load list of available tables/collections.

        Spatial components work with files rather than database tables,
        so this returns an empty list.
        """
        return []

    async def _read_data(self) -> Data:
        """Read data from spatial data source.

        This method should be overridden by concrete spatial components
        to implement their specific data reading logic.
        """
        msg = f"{self.__class__.__name__} must implement _read_data() method"
        raise NotImplementedError(msg)

    def _enrich_with_spatial_metadata(self, data_items: list[Data], gdf: Any) -> list[Data]:
        """Enrich Data objects with spatial metadata from GeoDataFrame.

        Args:
            data_items: List of Data objects to enrich
            gdf: GeoDataFrame containing spatial data

        Returns:
            List of Data objects with added spatial metadata
        """
        try:
            import geopandas as gpd
        except ImportError as e:
            msg = "GeoDataFrame processing requires 'geopandas' and 'shapely'. Install with: uv sync --group spatial"
            raise ImportError(msg) from e

        if not isinstance(gdf, gpd.GeoDataFrame):
            logger.warning("Input is not a GeoDataFrame, skipping spatial metadata enrichment")
            return data_items

        # Get CRS information
        crs = str(gdf.crs) if gdf.crs else "EPSG:4326"

        # Enrich each Data object with spatial metadata
        for i, data_item in enumerate(data_items):
            if i >= len(gdf):
                break

            row = gdf.iloc[i]
            geometry = row.geometry

            if geometry is not None:
                # Convert geometry to GeoJSON format
                import json

                geojson_geom = json.loads(geometry.to_json())

                # Store as standard GeoJSON "geometry" field
                data_item.data["geometry"] = geojson_geom
                data_item.data["_geometry_type"] = geometry.geom_type
                data_item.data["_crs"] = crs

                # Optionally add bounds for non-point geometries
                if geometry.geom_type not in ("Point", "MultiPoint"):
                    bounds = geometry.bounds
                    data_item.data["_bounds"] = {
                        "minx": bounds[0],
                        "miny": bounds[1],
                        "maxx": bounds[2],
                        "maxy": bounds[3],
                    }

        return data_items

    def _geodataframe_to_data(self, gdf: Any) -> list[Data]:
        """Convert GeoDataFrame to list of Data objects.

        Args:
            gdf: GeoDataFrame to convert

        Returns:
            List of Data objects with spatial metadata
        """
        try:
            import geopandas as gpd
        except ImportError as e:
            msg = "GeoDataFrame conversion requires 'geopandas'. Install with: uv sync --group spatial"
            raise ImportError(msg) from e

        if not isinstance(gdf, gpd.GeoDataFrame):
            msg = f"Expected GeoDataFrame, got {type(gdf)}"
            raise TypeError(msg)

        # Convert GeoDataFrame to regular DataFrame for attribute data
        df = pd.DataFrame(gdf.drop(columns="geometry"))

        # Create Data objects from DataFrame
        data_items = []
        for _, row in df.iterrows():
            data_dict = row.to_dict()
            data_items.append(Data(data=data_dict))

        # Enrich with spatial metadata
        return self._enrich_with_spatial_metadata(data_items, gdf)

    def _add_spatial_metadata_to_dataframe(self, df: pd.DataFrame, gdf: Any) -> pd.DataFrame:
        """Add spatial metadata to DataFrame for collection-level information.

        Args:
            df: DataFrame to add metadata to
            gdf: GeoDataFrame with spatial information

        Returns:
            DataFrame with spatial metadata attached
        """
        try:
            import geopandas as gpd
        except ImportError:
            return df

        if not isinstance(gdf, gpd.GeoDataFrame):
            return df

        # Store spatial metadata as DataFrame attribute
        df._spatial_metadata = {  # type: ignore[attr-defined]
            "crs": str(gdf.crs) if gdf.crs else "EPSG:4326",
            "geometry_column": gdf.geometry.name,
            "bounds": gdf.total_bounds.tolist() if hasattr(gdf, "total_bounds") else None,
            "feature_count": len(gdf),
        }

        return df


class BaseSpatialOutputComponent(BaseTableOutputComponent):
    """Base class for spatial output components.

    Extends BaseTableOutputComponent to support writing geographic data.
    Handles conversion from Data objects back to GeoDataFrame format.
    """

    def _extract_geodataframe(self, data_items: list[Data]) -> Any:
        """Extract GeoDataFrame from list of Data objects.

        Args:
            data_items: List of Data objects with spatial metadata

        Returns:
            GeoDataFrame reconstructed from Data objects
        """
        try:
            import geopandas as gpd
            from shapely import wkt as wkt_module
            from shapely.geometry import shape
        except ImportError as e:
            msg = "GeoDataFrame extraction requires 'geopandas' and 'shapely'. Install with: uv sync --group spatial"
            raise ImportError(msg) from e

        if not data_items:
            return gpd.GeoDataFrame()

        # Separate attribute data and geometry data
        attribute_rows = []
        geometries = []
        crs = None

        for data_item in data_items:
            data_dict = data_item.data.copy()

            # Priority 1: Try to read GeoJSON format (new format)
            geojson_geom = data_dict.pop("geometry", None)
            data_dict.pop("_geometry_type", None)
            data_dict.pop("_bounds", None)

            if crs is None:
                crs = data_dict.pop("_crs", "EPSG:4326")
            else:
                data_dict.pop("_crs", None)

            # Parse geometry
            if geojson_geom:
                try:
                    # Use shapely.geometry.shape() to create geometry from GeoJSON
                    geometry = shape(geojson_geom)
                    geometries.append(geometry)
                except Exception as e:
                    logger.warning("Failed to parse GeoJSON geometry: %s", e)
                    geometries.append(None)
            else:
                # Priority 2: Backward compatibility - try to read WKT format (legacy format)
                geometry_wkt = data_dict.pop("_geometry_wkt", None)
                if geometry_wkt:
                    try:
                        geometry = wkt_module.loads(geometry_wkt)
                        geometries.append(geometry)
                    except (ValueError, TypeError) as e:
                        logger.warning("Failed to parse WKT geometry: %s", e)
                        geometries.append(None)
                else:
                    geometries.append(None)

            attribute_rows.append(data_dict)

        # Create GeoDataFrame
        df = pd.DataFrame(attribute_rows)
        return gpd.GeoDataFrame(df, geometry=geometries, crs=crs)

    def _validate_spatial_data(self, gdf: Any) -> tuple[bool, str]:
        """Validate GeoDataFrame for spatial integrity.

        Args:
            gdf: GeoDataFrame to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            import geopandas as gpd
        except ImportError:
            return True, ""

        if not isinstance(gdf, gpd.GeoDataFrame):
            return False, "Input is not a GeoDataFrame"

        if gdf.empty:
            return False, "GeoDataFrame is empty"

        if gdf.geometry.name not in gdf.columns:
            return False, "Geometry column not found"

        # Check for invalid geometries
        invalid_count = (~gdf.geometry.is_valid).sum()
        if invalid_count > 0:
            return False, f"Found {invalid_count} invalid geometries"

        # Check for missing CRS
        if gdf.crs is None:
            logger.warning("GeoDataFrame has no CRS, defaulting to EPSG:4326")

        return True, ""
