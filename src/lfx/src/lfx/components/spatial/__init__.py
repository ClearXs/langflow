"""Spatial data components for LangFlow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx.components.spatial.gdb_create import GDBCreateComponent
    from lfx.components.spatial.gdb_import import GDBImportComponent
    from lfx.components.spatial.geojson_input import GeoJSONInputComponent
    from lfx.components.spatial.geotiff_input import GeoTIFFInputComponent
    from lfx.components.spatial.shapefile_input import ShapefileInputComponent
    from lfx.components.spatial.spatial_transform import SpatialTransformComponent

_dynamic_imports = {
    "GDBCreateComponent": "gdb_create",
    "GDBImportComponent": "gdb_import",
    "GeoJSONInputComponent": "geojson_input",
    "GeoTIFFInputComponent": "geotiff_input",
    "ShapefileInputComponent": "shapefile_input",
    "SpatialTransformComponent": "spatial_transform",
}

__all__ = [
    "GDBCreateComponent",
    "GDBImportComponent",
    "GeoJSONInputComponent",
    "GeoTIFFInputComponent",
    "ShapefileInputComponent",
    "SpatialTransformComponent",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import spatial components on attribute access."""
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)
