"""Spatial Transform Component.

Performs coordinate transformations and geographic entity encoding on spatial data.
"""

import json
from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class SpatialTransformComponent(Component):
    """Component for spatial coordinate transformation and geo-entity encoding."""

    display_name = i18n.t("components.spatial.spatial_transform.display_name")
    description = i18n.t("components.spatial.spatial_transform.description")
    icon = "move"
    name = "SpatialTransform"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.spatial.spatial_transform.data_input.display_name"),
            info=i18n.t("components.spatial.spatial_transform.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="transformation_rules",
            display_name=i18n.t("components.spatial.spatial_transform.transformation_rules.display_name"),
            info=i18n.t("components.spatial.spatial_transform.transformation_rules.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.field_name"),
                    "type": "str",
                    "formatter": "text",
                    "required": True,
                },
                {
                    "name": "field_type",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.field_type"),
                    "type": "str",
                    "formatter": "text",
                    "options": [
                        "string",
                        "integer",
                        "float",
                        "boolean",
                        "datetime",
                        "json",
                        "point",
                        "linestring",
                        "polygon",
                        "multipoint",
                        "multilinestring",
                        "multipolygon",
                        "geometry",
                        "geography",
                    ],
                    "required": False,
                },
                {
                    "name": "transformation_type",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.transformation_type"),
                    "type": "str",
                    "formatter": "text",
                    "options": ["none", "coordinate_transform", "geo_entity_encode"],
                    "options_metadata": [
                        {"value": "none", "label": i18n.t("components.spatial.spatial_transform.transformation_types.none")},
                        {"value": "coordinate_transform", "label": i18n.t("components.spatial.spatial_transform.transformation_types.coordinate_transform")},
                        {"value": "geo_entity_encode", "label": i18n.t("components.spatial.spatial_transform.transformation_types.geo_entity_encode")},
                    ],
                    "required": True,
                },
                {
                    "name": "source_crs",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.source_crs"),
                    "type": "str",
                    "formatter": "text",
                    "options": ["EPSG:4326", "EPSG:3857", "EPSG:4490", "EPSG:2000"],
                    "options_metadata": [
                        {"value": "EPSG:4326", "label": "EPSG:4326 (WGS84)"},
                        {"value": "EPSG:3857", "label": "EPSG:3857 (Web Mercator)"},
                        {"value": "EPSG:4490", "label": "EPSG:4490 (CGCS2000)"},
                        {"value": "EPSG:2000", "label": "EPSG:2000 (Aitoff)"},
                    ],
                },
                {
                    "name": "target_crs",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.target_crs"),
                    "type": "str",
                    "formatter": "text",
                    "options": ["EPSG:4326", "EPSG:3857", "EPSG:4490", "EPSG:2000"],
                    "options_metadata": [
                        {"value": "EPSG:4326", "label": "EPSG:4326 (WGS84)"},
                        {"value": "EPSG:3857", "label": "EPSG:3857 (Web Mercator)"},
                        {"value": "EPSG:4490", "label": "EPSG:4490 (CGCS2000)"},
                        {"value": "EPSG:2000", "label": "EPSG:2000 (Aitoff)"},
                    ],
                },
                {
                    "name": "entity_class_field",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.entity_class_field"),
                    "type": "str",
                },
                {
                    "name": "level",
                    "display_name": i18n.t("components.spatial.spatial_transform.transformation_rules.level"),
                    "type": "int",
                    "formatter": "number",
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_fields",
                        "label": i18n.t("components.spatial.spatial_transform.transformation_rules.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.spatial.spatial_transform.outputs.data.display_name"),
            method="transform_data",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,  # noqa: ARG002
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates based on action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (unused)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[SpatialTransform] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle analyze_fields action
        if field_name == "transformation_rules" and action == "analyze_fields":
            logger.info("[SpatialTransform] Field analysis triggered by action button")

            try:
                # Get graph_data and node_id
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[SpatialTransform] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[SpatialTransform] No graph data available")
                    self.status = i18n.t("components.spatial.spatial_transform.errors.no_graph_data")
                    return build_config

                # Extract upstream fields
                upstream_fields = await self._get_upstream_fields(graph_data, node_id)

                if upstream_fields:
                    # Populate transformation_rules table with all upstream fields
                    transformation_rules_config = build_config.get("transformation_rules", {})
                    if isinstance(transformation_rules_config, dict):
                        # Create table rows for all upstream fields
                        table_rows = []
                        for field in upstream_fields:
                            table_rows.append({
                                "field_name": field["name"],
                                "field_type": field["type"],
                                "transformation_type": "none",
                                "source_crs": "",
                                "target_crs": "",
                                "entity_class_field": "",
                                "level": 8,
                            })

                        # Update table value
                        transformation_rules_config["value"] = table_rows

                    self.status = i18n.t(
                        "components.spatial.spatial_transform.status.analysis_success",
                        count=len(upstream_fields),
                    )
                else:
                    self.status = i18n.t("components.spatial.spatial_transform.warnings.field_load_failed")

            except Exception:  # noqa: BLE001
                logger.exception("[SpatialTransform] Field analysis failed with unexpected error")
                self.status = i18n.t("components.spatial.spatial_transform.errors.graph_not_available")

        return build_config

    async def _get_upstream_fields(self, graph_data: dict, node_id: str) -> list[dict]:
        """Get fields from upstream node.

        Args:
            graph_data: Flow graph data
            node_id: Current node ID

        Returns:
            List of field info dicts: [{"name": "field1", "type": "string"}, ...]
        """
        try:
            # Try to execute upstream node to get actual data
            upstream_data = await self.get_upstream_data(
                input_name="data_input",
                graph_data=graph_data,
                sample_size=10,
                vertex_id=node_id,
            )

            if upstream_data:
                fields = self._extract_fields_from_data(upstream_data)
                logger.info(f"[SpatialTransform] Extracted {len(fields)} fields from upstream data")
                return fields

        except ValueError as e:
            logger.warning(f"[SpatialTransform] Upstream execution failed: {e}. Trying static analysis...")

        # Fallback: Try static analysis
        try:
            from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

            fields = find_and_extract_upstream_fields(graph_data, node_id, "data_input", "SpatialTransform")
            if fields:
                logger.info(f"[SpatialTransform] Extracted {len(fields)} fields from static config")
                return fields

        except Exception:  # noqa: BLE001
            logger.exception("[SpatialTransform] Static analysis also failed")

        return []

    def _extract_fields_from_data(self, data_list: list[Data]) -> list[dict]:
        """Extract field names and types from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field info dicts: [{"name": "field1", "type": "string"}, ...]
        """
        try:
            if not data_list:
                return []

            # Get first record
            first_record = data_list[0]
            if hasattr(first_record, "data"):
                data_dict = first_record.data
            elif isinstance(first_record, dict):
                data_dict = first_record
            else:
                logger.warning(f"[SpatialTransform] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[SpatialTransform] Expected dict, got {type(data_dict)}")
                return []

            # Extract fields
            fields = []
            for field_name, value in data_dict.items():
                # Infer type from value or field name
                field_type = self._infer_field_type(field_name, value)
                fields.append({"name": field_name, "type": field_type})

            logger.debug(f"[SpatialTransform] Extracted {len(fields)} fields")
            return fields

        except Exception:  # noqa: BLE001
            logger.exception("[SpatialTransform] Failed to extract fields from data")
            return []

    def _infer_field_type(self, field_name: str, value: Any) -> str:
        """Infer field type from field name and value.

        Args:
            field_name: Field name
            value: Field value

        Returns:
            Inferred type string
        """
        # Check if geometry-related field by name
        geometry_field_names = {"geometry", "geom", "shape", "wkt", "_geometry_wkt"}
        if field_name in geometry_field_names:
            return "geometry"

        # Check if it's a GeoJSON geometry
        if isinstance(value, dict) and "type" in value and "coordinates" in value:
            return "geometry"

        # Check if it's JSON (dict or list that's NOT GeoJSON)
        if isinstance(value, (dict, list)):
            return "json"

        # Infer from value type
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"

        return "text"

    async def transform_data(self) -> list[Data]:
        """Execute spatial transformations on input data.

        Returns:
            List of transformed Data objects

        Raises:
            ValueError: If configuration is invalid or transformation fails
        """
        try:
            # Validate inputs
            if not self.data_input:
                raise ValueError(i18n.t("components.spatial.spatial_transform.errors.no_data"))

            if not self.transformation_rules:
                raise ValueError(i18n.t("components.spatial.spatial_transform.errors.no_rules"))

            self.status = i18n.t("components.spatial.spatial_transform.status.processing")

            # Get Feign client
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.gis_transform import GISTransformFeignClient

            feign_service = get_feign_service()
            gis_client = GISTransformFeignClient(feign_service)

            # Process each data record
            result_data = []
            data_items = self.data_input if isinstance(self.data_input, list) else [self.data_input]

            for data_item in data_items:
                # Extract row dictionary
                row_dict = (
                    data_item.data if hasattr(data_item, "data") and isinstance(data_item.data, dict) else data_item
                )

                if not isinstance(row_dict, dict):
                    logger.warning(f"[SpatialTransform] Expected dict but got {type(row_dict)}: {row_dict}")
                    continue

                # Apply transformation rules
                for rule in self.transformation_rules:
                    row_dict = await self._apply_transformation_rule(row_dict, rule, gis_client)

                result_data.append(Data(data=row_dict))

            self.status = i18n.t(
                "components.spatial.spatial_transform.status.success",
                count=len(result_data),
            )
            logger.info(f"[SpatialTransform] Transformed {len(result_data)} records")

            return result_data

        except Exception as e:
            error_msg = i18n.t("components.spatial.spatial_transform.errors.transform_failed", error=str(e))
            self.status = error_msg
            logger.exception("[SpatialTransform] Transformation failed")
            raise ValueError(error_msg) from e

    async def _apply_transformation_rule(
        self,
        row_dict: dict,
        rule: dict,
        gis_client: Any,
    ) -> dict:
        """Apply single transformation rule to row data.

        Args:
            row_dict: Row data dictionary
            rule: Transformation rule configuration
            gis_client: GIS transform Feign client

        Returns:
            Transformed row dictionary
        """
        field_name = rule.get("field_name")
        field_type = rule.get("field_type", "text")
        transformation_type = rule.get("transformation_type")

        # Initialize field if it doesn't exist (for new fields)
        if field_name and field_name not in row_dict:
            if field_type in ("integer", "int"):
                row_dict[field_name] = 0
            elif field_type in ("float", "double"):
                row_dict[field_name] = 0.0
            elif field_type == "boolean":
                row_dict[field_name] = False
            else:
                row_dict[field_name] = None

        if transformation_type == "coordinate_transform":
            return await self._apply_coordinate_transform(row_dict, rule, gis_client)
        if transformation_type == "geo_entity_encode":
            return await self._apply_geo_entity_encode(row_dict, rule, gis_client)
        if transformation_type == "none":
            return row_dict

        logger.warning(f"[SpatialTransform] Unknown transformation type: {transformation_type}")
        return row_dict

    async def _apply_coordinate_transform(
        self,
        row_dict: dict,
        rule: dict,
        gis_client: Any,
    ) -> dict:
        """Apply coordinate transformation to a geometry field.

        Args:
            row_dict: Row data dictionary
            rule: Transformation rule
            gis_client: GIS transform client

        Returns:
            Row dictionary with transformed geometry
        """
        field_name = rule.get("field_name")
        if not field_name:
            logger.warning("[SpatialTransform] No field_name specified for coordinate transform")
            return row_dict

        # Get geometry from field
        geometry = self._get_geometry_from_field(row_dict, field_name)
        if not geometry:
            logger.warning(f"[SpatialTransform] No geometry found in field {field_name}")
            return row_dict

        try:
            # Transform geometry based on type
            geom_type = geometry.get("type")
            coordinates = geometry.get("coordinates")

            if geom_type == "Point":
                transformed_coords = await self._transform_point(coordinates, rule, gis_client)
                geometry["coordinates"] = transformed_coords

            elif geom_type in ("LineString", "MultiPoint"):
                transformed_coords = await self._transform_coordinates_array(coordinates, rule, gis_client)
                geometry["coordinates"] = transformed_coords

            elif geom_type in ("Polygon", "MultiLineString"):
                transformed_coords = await self._transform_nested_coordinates(coordinates, rule, gis_client)
                geometry["coordinates"] = transformed_coords

            elif geom_type == "MultiPolygon":
                transformed_coords = await self._transform_multi_nested_coordinates(coordinates, rule, gis_client)
                geometry["coordinates"] = transformed_coords

            else:
                logger.warning(f"[SpatialTransform] Unsupported geometry type: {geom_type}")

            # Update geometry in row
            row_dict[field_name] = geometry

        except Exception as e:
            logger.error(f"[SpatialTransform] Coordinate transform failed for field {field_name}: {e}")
            # Keep original geometry on error

        return row_dict

    async def _apply_geo_entity_encode(
        self,
        row_dict: dict,
        rule: dict,
        gis_client: Any,
    ) -> dict:
        """Apply geographic entity encoding.

        Args:
            row_dict: Row data dictionary
            rule: Transformation rule
            gis_client: GIS transform client

        Returns:
            Row dictionary with encoded entity
        """
        output_field = rule.get("field_name")
        if not output_field:
            logger.warning("[SpatialTransform] No field_name specified for geo entity encode")
            return row_dict

        entity_class_field = rule.get("entity_class_field")
        if not entity_class_field:
            logger.warning("[SpatialTransform] No entity_class_field specified")
            return row_dict

        entity_class = row_dict.get(entity_class_field)
        if not entity_class:
            logger.warning(f"[SpatialTransform] Entity class not found in field: {entity_class_field}")
            return row_dict

        # Find geometry field (try common names)
        geometry = None
        for geom_field in ("geometry", "geom", "shape", "wkt"):
            geometry = self._get_geometry_from_field(row_dict, geom_field)
            if geometry:
                break

        if not geometry:
            logger.warning("[SpatialTransform] No geometry found for geo entity encode")
            return row_dict

        try:
            level = rule.get("level", 8)
            entity_code = await gis_client.encode_geo_entity(
                geometry=geometry,
                entity_class_name=entity_class,
                level=level,
            )

            # Write to output field
            row_dict[output_field] = entity_code

        except Exception as e:
            logger.error(f"[SpatialTransform] Geo entity encoding failed: {e}")
            row_dict[output_field] = None  # Set to None on error

        return row_dict

    def _get_geometry_from_field(self, row_dict: dict, field_name: str) -> dict | None:
        """Get GeoJSON geometry from a field.

        Args:
            row_dict: Row data dictionary
            field_name: Field name

        Returns:
            GeoJSON geometry dict or None
        """
        if field_name not in row_dict:
            return None

        geometry = row_dict[field_name]

        # Already GeoJSON dict format
        if isinstance(geometry, dict) and "type" in geometry and "coordinates" in geometry:
            return geometry

        # Try parsing as JSON string
        if isinstance(geometry, str):
            try:
                parsed = json.loads(geometry)
                if isinstance(parsed, dict) and "type" in parsed and "coordinates" in parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # Maybe WKT format, try converting
                try:
                    from shapely import wkt as wkt_module

                    shapely_geom = wkt_module.loads(geometry)
                    return json.loads(shapely_geom.__geo_interface__)
                except Exception:  # noqa: BLE001
                    logger.warning(f"[SpatialTransform] Failed to parse geometry from field {field_name}")

        return None

    async def _transform_point(
        self,
        coordinates: list[float],
        rule: dict,
        gis_client: Any,
    ) -> list[float]:
        """Transform a single point's coordinates.

        Args:
            coordinates: Point coordinates [x, y] or [x, y, z]
            rule: Transformation rule
            gis_client: GIS transform client

        Returns:
            Transformed coordinates
        """
        try:
            x, y = coordinates[0], coordinates[1]
            z = coordinates[2] if len(coordinates) > 2 else None

            source_crs = rule.get("source_crs", "EPSG:4326")
            target_crs = rule.get("target_crs", "EPSG:3857")

            transformed = await gis_client.transform_coordinate(
                x=x,
                y=y,
                z=z,
                source_crs=source_crs,
                target_crs=target_crs,
            )

            return transformed

        except Exception as e:
            logger.error(f"[SpatialTransform] Point transform failed: {e}")
            return coordinates  # Return original on error

    async def _transform_coordinates_array(
        self,
        coordinates: list[list[float]],
        rule: dict,
        gis_client: Any,
    ) -> list[list[float]]:
        """Transform array of coordinates (LineString, MultiPoint).

        Args:
            coordinates: List of coordinate points
            rule: Transformation rule
            gis_client: GIS transform client

        Returns:
            Transformed coordinates array
        """
        transformed = []
        for coord in coordinates:
            transformed_coord = await self._transform_point(coord, rule, gis_client)
            transformed.append(transformed_coord)
        return transformed

    async def _transform_nested_coordinates(
        self,
        coordinates: list[list[list[float]]],
        rule: dict,
        gis_client: Any,
    ) -> list[list[list[float]]]:
        """Transform nested coordinates array (Polygon, MultiLineString).

        Args:
            coordinates: Nested list of coordinate points
            rule: Transformation rule
            gis_client: GIS transform client

        Returns:
            Transformed nested coordinates
        """
        transformed = []
        for ring in coordinates:
            transformed_ring = await self._transform_coordinates_array(ring, rule, gis_client)
            transformed.append(transformed_ring)
        return transformed

    async def _transform_multi_nested_coordinates(
        self,
        coordinates: list[list[list[list[float]]]],
        rule: dict,
        gis_client: Any,
    ) -> list[list[list[list[float]]]]:
        """Transform multi-nested coordinates (MultiPolygon).

        Args:
            coordinates: Multi-nested list of coordinate points
            rule: Transformation rule
            gis_client: GIS transform client

        Returns:
            Transformed multi-nested coordinates
        """
        transformed = []
        for polygon in coordinates:
            transformed_polygon = await self._transform_nested_coordinates(polygon, rule, gis_client)
            transformed.append(transformed_polygon)
        return transformed
