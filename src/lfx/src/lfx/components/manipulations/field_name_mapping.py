import asyncio
from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLFieldNameMappingComponent(Component):
    display_name = i18n.t("components.manipulations.field_name_mapping.display_name")
    description = i18n.t("components.manipulations.field_name_mapping.description")
    icon = "shuffle"
    name = "ETLFieldNameMapping"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_name_mapping.data_input.display_name"),
            info=i18n.t("components.manipulations.field_name_mapping.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t("components.manipulations.field_name_mapping.field_mappings.display_name"),
            info=i18n.t("components.manipulations.field_name_mapping.field_mappings.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t("components.manipulations.field_name_mapping.field_mappings.source_field"),
                    "type": "str",
                    "description": i18n.t(
                        "components.manipulations.field_name_mapping.field_mappings.source_field_desc"
                    ),
                },
                {
                    "name": "target_field",
                    "display_name": i18n.t("components.manipulations.field_name_mapping.field_mappings.target_field"),
                    "type": "str",
                    "description": i18n.t(
                        "components.manipulations.field_name_mapping.field_mappings.target_field_desc"
                    ),
                },
                {
                    "name": "description",
                    "display_name": i18n.t("components.manipulations.field_name_mapping.field_mappings.description"),
                    "type": "str",
                    "description": i18n.t(
                        "components.manipulations.field_name_mapping.field_mappings.description_desc"
                    ),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_fields",
                        "label": i18n.t("components.manipulations.field_name_mapping.field_mappings.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        BoolInput(
            name="drop_unmapped",
            display_name=i18n.t("components.manipulations.field_name_mapping.drop_unmapped.display_name"),
            info=i18n.t("components.manipulations.field_name_mapping.drop_unmapped.info"),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_name_mapping.outputs.data.display_name"),
            method="map_field_names",
        )
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates based on action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (unused in this implementation)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[FieldNameMapping] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle action button clicks (from field_mappings table)
        if field_name == "field_mappings" and action == "analyze_fields":
            logger.info("[FieldNameMapping] Field analysis triggered by action button")

            try:
                # Try to get graph_data and node_id from build_config first (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        # PlaceholderGraph - no data available
                        logger.warning("[FieldNameMapping] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[FieldNameMapping] No graph data available")
                    self.status = i18n.t("components.manipulations.field_name_mapping.errors.no_graph_data")
                    return build_config

                field_mappings = []

                # Primary strategy: Try to execute upstream node to get actual data
                # Enhanced with retry mechanism for "has not been built yet" errors
                max_retries = 2
                upstream_data = None

                for attempt in range(max_retries):
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )

                        if upstream_data:
                            # Extract field names from upstream data
                            field_mappings = self._extract_field_mappings(upstream_data)
                            logger.info(f"[FieldNameMapping] Extracted {len(field_mappings)} field mappings from upstream data (attempt {attempt + 1})")
                            break
                        else:
                            logger.warning(f"[FieldNameMapping] No data returned from upstream node (attempt {attempt + 1})")

                    except ValueError as e:
                        error_msg = str(e)
                        if "has not been built yet" in error_msg and attempt < max_retries - 1:
                            logger.warning(f"[FieldNameMapping] Upstream node not built, retrying... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(0.2)  # Brief delay before retry
                            continue
                        else:
                            # Fallback strategy: Extract from upstream node configuration
                            logger.warning(f"[FieldNameMapping] Upstream execution failed after {attempt + 1} attempts: {e}. Trying static analysis...")
                            break
                    except Exception as e:
                        logger.warning(f"[FieldNameMapping] Unexpected error during upstream execution: {e}. Falling back to static analysis...")
                        break

                # If we couldn't get data from execution, try static analysis
                if not upstream_data:
                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        field_names = find_and_extract_upstream_fields(
                            graph_data, node_id, "data_input", "FieldNameMapping"
                        )

                        if field_names:
                            # Generate field mappings from field names
                            field_mappings = [
                                {
                                    "source_field": field_name,
                                    "target_field": field_name,  # Default: same as source
                                    "description": "",  # Empty description by default
                                }
                                for field_name in field_names
                            ]
                            logger.info(
                                f"[FieldNameMapping] Extracted {len(field_mappings)} field mappings from static config"
                            )
                        else:
                            logger.warning("[FieldNameMapping] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[FieldNameMapping] Static analysis also failed")

                # Update build_config with results
                if field_mappings:
                    build_config["field_mappings"]["value"] = field_mappings
                    self.status = i18n.t(
                        "components.manipulations.field_name_mapping.status.analysis_success", count=len(field_mappings)
                    )
                else:
                    self.status = i18n.t("components.manipulations.field_name_mapping.warnings.field_load_failed")
                    logger.warning("[FieldNameMapping] No fields extracted from upstream data")

            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[FieldNameMapping] Field analysis failed with unexpected error")
                self.status = i18n.t("components.manipulations.field_name_mapping.errors.graph_not_available")

        logger.debug(f"[FieldNameMapping] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _extract_field_mappings(self, data_list: list[Data]) -> list[dict]:
        """Extract field mappings from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field mapping dictionaries with source_field, target_field, description
        """
        try:
            if not data_list:
                return []

            # Get first record to extract field names
            first_record = data_list[0]
            if hasattr(first_record, "data"):
                data_dict = first_record.data
            elif isinstance(first_record, dict):
                data_dict = first_record
            else:
                logger.warning(f"[FieldNameMapping] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[FieldNameMapping] Expected dict, got {type(data_dict)}")
                return []

            # Generate field mappings from field names
            field_mappings = [
                {
                    "source_field": field_name,
                    "target_field": field_name,  # Default: same as source
                    "description": "",  # Empty description by default
                }
                for field_name in data_dict
            ]

            logger.debug(f"[FieldNameMapping] Extracted {len(field_mappings)} field mappings")
            return field_mappings

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[FieldNameMapping] Failed to extract field mappings")
            return []

    def map_field_names(self) -> list[Data]:
        """Map source field names to target field names."""
        try:
            if not self.data_input or not self.field_mappings:
                raise ValueError(i18n.t("components.manipulations.field_name_mapping.errors.missing_config"))

            # Handle both single Data objects and lists of Data objects
            data_items = self.data_input
            if not isinstance(data_items, list):
                data_items = [data_items]

            # Convert to DataFrame with proper error handling
            processed_data = []
            for d in data_items:
                if hasattr(d, "data") and isinstance(d.data, dict):
                    processed_data.append(d.data)
                elif isinstance(d, dict):
                    processed_data.append(d)
                elif isinstance(d, tuple):
                    # Handle tuple case - try to extract meaningful data
                    logger.warning(f"Received tuple instead of Data object: {d}")
                    if len(d) >= 2 and isinstance(d[1], dict):
                        processed_data.append(d[1])  # Use the second element if it's a dict
                    else:
                        logger.error(f"Cannot process tuple: {d}")
                        continue
                else:
                    logger.warning(f"Unknown data type {type(d)}: {d}")
                    continue

            df = pd.DataFrame(processed_data)

            # Strip whitespace from column names to normalize field names
            df.columns = df.columns.str.strip()

            # Log available fields for debugging
            logger.info(f"[FieldNameMapping] Available fields in input data: {list(df.columns)}")
            logger.info(f"[FieldNameMapping] Field mappings to apply: {self.field_mappings}")

            # Build mapping dictionary and validate
            mapping_dict = {}
            target_fields_seen = set()

            for mapping in self.field_mappings:
                source = mapping.get("source_field", "").strip()
                target = mapping.get("target_field", "").strip()

                if not source or not target:
                    logger.warning(f"[FieldNameMapping] Skipping empty mapping: {mapping}")
                    continue

                # Validate source field exists
                if source not in df.columns:
                    available_fields = ", ".join(df.columns)
                    error_msg = i18n.t(
                        "components.manipulations.field_name_mapping.errors.source_field_not_found", field=source
                    )
                    detailed_error = f"{error_msg}. Available fields: {available_fields}"
                    logger.error(f"[FieldNameMapping] {detailed_error}")
                    raise ValueError(detailed_error)

                # Check for duplicate target fields
                if target in target_fields_seen:
                    error_msg = i18n.t(
                        "components.manipulations.field_name_mapping.errors.duplicate_target_field", field=target
                    )
                    logger.error(f"[FieldNameMapping] {error_msg}")
                    raise ValueError(error_msg)

                target_fields_seen.add(target)
                mapping_dict[source] = target

            logger.info(f"[FieldNameMapping] Applying field mappings: {mapping_dict}")

            # Apply field name mapping
            df = df.rename(columns=mapping_dict)

            # Optionally drop unmapped fields
            if self.drop_unmapped:
                mapped_fields = list(mapping_dict.values())
                df = df[mapped_fields]
                logger.info(f"[FieldNameMapping] Dropped unmapped fields, remaining: {list(df.columns)}")

            # Convert back to Data objects
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]

            # Success status
            self.status = i18n.t(
                "components.manipulations.field_name_mapping.status.success",
                count=len(result),
                fields=len(mapping_dict),
            )

            logger.info(
                f"[FieldNameMapping] Successfully mapped {len(result)} records with {len(mapping_dict)} field transformations"
            )

            return result

        except ValueError:
            # Re-raise ValueError directly without wrapping
            raise
        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_name_mapping.errors.mapping_failed", error=str(e))
            logger.exception(f"[FieldNameMapping] {error_msg}")
            self.status = error_msg
            raise ValueError(error_msg) from e
