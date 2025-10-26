"""Custom Input Component for ETL operations."""

import random
from datetime import datetime
from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, IntInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


def _format_i18n(key: str, **kwargs) -> str:
    """Helper function to format i18n strings with parameters.

    The i18n library's parameter substitution doesn't work properly,
    so we manually replace {param} placeholders.
    """
    text = i18n.t(key)
    for param_key, param_value in kwargs.items():
        text = text.replace(f"{{{param_key}}}", str(param_value))
    return text


# Sample data generators for test data
SAMPLE_FIRST_NAMES = [
    "James",
    "Mary",
    "John",
    "Patricia",
    "Robert",
    "Jennifer",
    "Michael",
    "Linda",
    "William",
    "Barbara",
    "David",
    "Elizabeth",
    "Richard",
    "Susan",
    "Joseph",
    "Jessica",
]

SAMPLE_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
]

SAMPLE_EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "example.com", "test.com"]


class ETLCustomInputComponent(Component):
    """Custom data input component with user-defined schema for testing."""

    display_name = i18n.t("components.input_output.custom_input.display_name")
    description = i18n.t("components.input_output.custom_input.description")
    icon = "TestTube2"
    name = "ETLCustomInput"

    inputs = [
        TableInput(
            name="field_schema",
            display_name=i18n.t("components.input_output.custom_input.field_schema.display_name"),
            info=i18n.t("components.input_output.custom_input.field_schema.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.field_name"),
                    "type": "str",
                    "required": True,
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.data_type"),
                    "type": "str",
                    "formatter": "text",
                    "options": ["string", "integer", "float", "boolean", "datetime"],
                },
                {
                    "name": "default_value",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.default_value"),
                    "type": "str",
                },
            ],
            value=[],
            table_options={
                "block_add": False,  # Allow adding fields
                "block_delete": False,  # Allow deleting fields
                "block_edit": False,  # Allow editing
                # Removed apply_schema button - auto-sync on field_schema change
            },
            advanced=False,
        ),
        TableInput(
            name="data_table",
            display_name=i18n.t("components.input_output.custom_input.data_table.display_name"),
            info=i18n.t("components.input_output.custom_input.data_table.info"),
            table_schema=[],  # Will be dynamically generated from field_schema
            value=[],
            table_options={
                "block_add": False,
                "block_delete": False,
                "block_edit": False,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "generate_test_data",
                        "label": i18n.t("components.input_output.custom_input.data_table.generate_button"),
                        "icon": "Sparkles",
                        "position": "top",
                    },
                    {
                        "name": "validate_data",
                        "label": i18n.t("components.input_output.custom_input.data_table.validate_button"),
                        "icon": "CheckCircle",
                        "position": "top",
                    },
                ],
            },
            advanced=False,
        ),
        IntInput(
            name="test_rows_count",
            display_name=i18n.t("components.input_output.custom_input.test_rows_count.display_name"),
            info=i18n.t("components.input_output.custom_input.test_rows_count.info"),
            value=10,
            range_spec={"min": 1, "max": 1000},
            advanced=True,
        ),
        BoolInput(
            name="strict_validation",
            display_name=i18n.t("components.input_output.custom_input.strict_validation.display_name"),
            info=i18n.t("components.input_output.custom_input.strict_validation.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.custom_input.output_data.display_name"),
            method="load_data",
        ),
    ]

    def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Handle dynamic configuration updates and action buttons."""
        logger.info(
            f"[CustomInput] update_build_config called - field_name: {field_name}, "
            f"field_value type: {type(field_value).__name__ if field_value is not None else 'None'}, "
            f"action: {action}"
        )

        # ALWAYS sync schema on ANY update_build_config call
        # This ensures data_table schema is always in sync with field_schema
        try:
            field_schema = build_config.get("field_schema", {}).get("value", [])
            current_data_schema = build_config.get("data_table", {}).get("table_schema", [])

            # Only update if we have a field_schema
            if field_schema:
                # Generate expected schema
                expected_schema = self._generate_schema_from_fields(field_schema)

                # Check if schema needs update
                schema_changed = len(current_data_schema) != len(expected_schema)
                if not schema_changed and len(expected_schema) > 0:
                    # Check if field names match
                    current_names = {f.get("name") for f in current_data_schema}
                    expected_names = {f.get("name") for f in expected_schema}
                    schema_changed = current_names != expected_names

                if schema_changed:
                    logger.info(
                        f"[CustomInput] Schema out of sync, updating data_table schema with {len(expected_schema)} fields"
                    )
                    build_config["data_table"]["table_schema"] = expected_schema

                    # Clear data if schema structure changed
                    # BUT DO NOT clear if user is about to generate test data or validate
                    # because those actions will populate/check the data
                    if action not in ("generate_test_data", "validate_data"):
                        existing_data = build_config.get("data_table", {}).get("value", [])
                        if existing_data:
                            logger.info("[CustomInput] Clearing existing data due to schema change")
                            build_config["data_table"]["value"] = []
                    else:
                        logger.info(f"[CustomInput] Schema synced but NOT clearing data because action={action}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[CustomInput] Error during auto-sync: {e}")

        # Handle explicit field_schema changes (from user editing the table)
        if field_name == "field_schema":
            logger.info("[CustomInput] Field schema explicitly changed by user")
            try:
                field_schema = build_config.get("field_schema", {}).get("value", [])

                if not field_schema:
                    # Clear data_table if schema is empty
                    build_config["data_table"]["table_schema"] = []
                    build_config["data_table"]["value"] = []
                    self.status = i18n.t("components.input_output.custom_input.status.schema_cleared")
                    logger.info("[CustomInput] Schema cleared")
                    return build_config

                # Validate schema for duplicate field names
                field_names = [field.get("field_name") for field in field_schema if field.get("field_name")]
                if len(field_names) != len(set(field_names)):
                    # Find duplicates
                    duplicates = [name for name in field_names if field_names.count(name) > 1]
                    duplicate_name = duplicates[0] if duplicates else "unknown"
                    self.status = _format_i18n(
                        "components.input_output.custom_input.errors.duplicate_field", name=duplicate_name
                    )
                    logger.error(f"[CustomInput] Duplicate field name: {duplicate_name}")
                    return build_config

                # Generate data table schema (already done in auto-sync above)
                data_table_schema = self._generate_schema_from_fields(field_schema)
                build_config["data_table"]["table_schema"] = data_table_schema

                self.status = _format_i18n(
                    "components.input_output.custom_input.status.schema_applied", count=len(data_table_schema)
                )
                logger.info(f"[CustomInput] User-triggered schema update with {len(data_table_schema)} fields")

            except Exception as e:  # noqa: BLE001 - Catch all for config updates
                error_msg = str(e)
                self.status = _format_i18n(
                    "components.input_output.custom_input.errors.validation_failed", error=error_msg
                )
                logger.exception(f"[CustomInput] Failed to sync schema: {error_msg}")

        # Handle "Generate Test Data" action
        if field_name == "data_table" and action == "generate_test_data":
            logger.info("[CustomInput] Generate test data action triggered")
            try:
                # Get current field schema
                field_schema = build_config.get("field_schema", {}).get("value", [])

                if not field_schema:
                    self.status = i18n.t("components.input_output.custom_input.errors.no_schema")
                    logger.warning("[CustomInput] No field schema defined for test data generation")
                    return build_config

                # Get test rows count
                test_rows_count = build_config.get("test_rows_count", {}).get("value", 10)

                # Generate test data
                test_data = self._generate_test_data(field_schema, test_rows_count)

                # DEBUG: Log generated data details
                logger.info(
                    f"[CustomInput] Generated test data sample (first row): {test_data[0] if test_data else 'EMPTY'}"
                )
                logger.info(f"[CustomInput] Total rows generated: {len(test_data)}")
                logger.info(
                    f"[CustomInput] Current data_table schema: {build_config.get('data_table', {}).get('table_schema', [])}"
                )

                # Update data_table with test data
                build_config["data_table"]["value"] = test_data

                # DEBUG: Verify the update
                logger.info(
                    f"[CustomInput] After update, data_table value has {len(build_config['data_table']['value'])} rows"
                )

                self.status = _format_i18n(
                    "components.input_output.custom_input.status.test_data_generated", count=len(test_data)
                )
                logger.info(f"[CustomInput] Generated {len(test_data)} test data rows")

            except Exception as e:  # noqa: BLE001 - Catch all for config updates
                error_msg = str(e)
                self.status = _format_i18n(
                    "components.input_output.custom_input.errors.validation_failed", error=error_msg
                )
                logger.exception(f"[CustomInput] Failed to generate test data: {error_msg}")

        # Handle "Validate Data" action
        if field_name == "data_table" and action == "validate_data":
            logger.info("[CustomInput] Validate data action triggered")
            try:
                # Get current field schema
                field_schema = build_config.get("field_schema", {}).get("value", [])

                if not field_schema:
                    self.status = i18n.t("components.input_output.custom_input.errors.no_schema")
                    logger.warning("[CustomInput] No field schema defined for validation")
                    return build_config

                # Get current data
                data_table = build_config.get("data_table", {}).get("value", [])

                if not data_table:
                    self.status = i18n.t("components.input_output.custom_input.errors.no_data")
                    logger.warning("[CustomInput] No data to validate")
                    return build_config

                # Get strict validation setting
                strict_validation = build_config.get("strict_validation", {}).get("value", True)

                # Validate all rows
                for idx, row in enumerate(data_table):
                    self._validate_data_row(row, field_schema, strict_validation, row_index=idx)

                self.status = _format_i18n(
                    "components.input_output.custom_input.status.validation_passed", count=len(data_table)
                )
                logger.info(f"[CustomInput] All {len(data_table)} rows validated successfully")

            except Exception as e:  # noqa: BLE001 - Catch all for config updates
                error_msg = str(e)
                self.status = _format_i18n(
                    "components.input_output.custom_input.errors.validation_failed", error=error_msg
                )
                logger.exception(f"[CustomInput] Data validation failed: {error_msg}")

        return build_config

    def _generate_schema_from_fields(self, field_schema: list[dict]) -> list[dict]:
        """Convert field schema rows to TableInput table_schema format.

        Args:
            field_schema: List of field definitions with field_name, data_type, default_value

        Returns:
            List of table schema definitions for TableInput
        """
        table_schema = []

        for field in field_schema:
            field_name = field.get("field_name")
            data_type = field.get("data_type", "string")

            if not field_name:
                continue

            # Map data types to frontend types
            frontend_type = "str"  # Default
            if data_type == "integer":
                frontend_type = "int"
            elif data_type == "float":
                frontend_type = "float"
            elif data_type == "boolean":
                frontend_type = "bool"
            elif data_type == "datetime":
                frontend_type = "str"  # DateTime rendered as string in table

            table_schema.append(
                {
                    "name": field_name,
                    "display_name": field_name,
                    "type": frontend_type,
                    "disable_edit": False,  # Allow editing
                }
            )

        return table_schema

    def _generate_test_data(self, field_schema: list[dict], row_count: int) -> list[dict]:
        """Generate test data based on field schema.

        Args:
            field_schema: List of field definitions
            row_count: Number of rows to generate

        Returns:
            List of data rows (dictionaries)
        """
        test_data = []

        for i in range(row_count):
            row = {}
            for field in field_schema:
                field_name = field.get("field_name")
                data_type = field.get("data_type", "string")
                default_value = field.get("default_value", "")

                if not field_name:
                    continue

                # Generate sample value based on type
                value = self._generate_sample_value(field_name, data_type, i)

                # Use default value if specified and it's the first row
                if i == 0 and default_value:
                    try:
                        value = self._convert_value(default_value, data_type)
                    except Exception:
                        # If conversion fails, use generated value
                        pass

                row[field_name] = value

            test_data.append(row)

        return test_data

    def _generate_sample_value(self, field_name: str, data_type: str, index: int) -> Any:
        """Generate realistic sample value based on field name and type.

        Args:
            field_name: Name of the field
            data_type: Data type of the field
            index: Row index for generating unique values

        Returns:
            Sample value of appropriate type
        """
        field_name_lower = field_name.lower()

        if data_type == "string":
            # Generate contextual strings based on field name
            if "name" in field_name_lower and "first" in field_name_lower:
                return random.choice(SAMPLE_FIRST_NAMES)
            if "name" in field_name_lower and "last" in field_name_lower:
                return random.choice(SAMPLE_LAST_NAMES)
            if "name" in field_name_lower:
                return f"{random.choice(SAMPLE_FIRST_NAMES)} {random.choice(SAMPLE_LAST_NAMES)}"
            if "email" in field_name_lower:
                first = random.choice(SAMPLE_FIRST_NAMES).lower()
                last = random.choice(SAMPLE_LAST_NAMES).lower()
                domain = random.choice(SAMPLE_EMAIL_DOMAINS)
                return f"{first}.{last}@{domain}"
            if "address" in field_name_lower or "street" in field_name_lower:
                return f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Park'])} St"
            if "city" in field_name_lower:
                return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])
            if "state" in field_name_lower:
                return random.choice(["CA", "NY", "TX", "FL", "IL"])
            if "country" in field_name_lower:
                return random.choice(["USA", "Canada", "UK", "Germany", "France"])
            if "phone" in field_name_lower:
                return f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            if "description" in field_name_lower or "comment" in field_name_lower:
                return f"Sample description for record {index + 1}"
            return f"sample_{field_name}_{index + 1}"

        if data_type == "integer":
            # Generate contextual integers
            if "id" in field_name_lower:
                return index + 1
            if "age" in field_name_lower:
                return random.randint(18, 80)
            if "year" in field_name_lower:
                return random.randint(2000, 2025)
            if "count" in field_name_lower or "total" in field_name_lower:
                return random.randint(0, 1000)
            return random.randint(1, 100)

        if data_type == "float":
            # Generate contextual floats
            if "price" in field_name_lower or "cost" in field_name_lower or "amount" in field_name_lower:
                return round(random.uniform(10.0, 1000.0), 2)
            if "rate" in field_name_lower or "percent" in field_name_lower:
                return round(random.uniform(0.0, 100.0), 2)
            if "score" in field_name_lower:
                return round(random.uniform(0.0, 10.0), 2)
            return round(random.uniform(0.0, 100.0), 2)

        if data_type == "boolean":
            return random.choice([True, False])

        if data_type == "datetime":
            # Generate random datetime in past year
            year = random.randint(2024, 2025)
            month = random.randint(1, 12)
            day = random.randint(1, 28)  # Safe day range
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            return datetime(year, month, day, hour, minute).isoformat()

        return ""

    def _convert_value(self, value: Any, data_type: str) -> Any:
        """Convert value to target data type.

        Args:
            value: Input value (typically string from UI)
            data_type: Target data type

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
        """
        if value is None or value == "":
            return None

        try:
            if data_type == "string":
                return str(value)

            if data_type == "integer":
                return int(value)

            if data_type == "float":
                return float(value)

            if data_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    value_lower = value.lower().strip()
                    if value_lower in ("true", "1", "yes", "y", "on"):
                        return True
                    if value_lower in ("false", "0", "no", "n", "off"):
                        return False
                    raise ValueError(f"Cannot convert '{value}' to boolean")
                return bool(value)

            if data_type == "datetime":
                if isinstance(value, datetime):
                    return value.isoformat()
                # Try to parse datetime string
                try:
                    dt = pd.to_datetime(value)
                    return dt.isoformat()
                except Exception as e:
                    raise ValueError(f"Cannot parse datetime: {e}")

            else:
                return str(value)

        except (ValueError, TypeError) as e:
            raise ValueError(
                _format_i18n(
                    "components.input_output.custom_input.errors.type_conversion_failed",
                    value=str(value),
                    type=data_type,
                )
            ) from e

    def _validate_data_row(
        self, row: dict, field_schema: list[dict], strict_validation: bool = True, row_index: int = 0
    ) -> dict:
        """Validate single data row against schema.

        Args:
            row: Data row to validate
            field_schema: Field schema definitions
            strict_validation: Whether to enforce strict type checking
            row_index: Row index for error reporting

        Returns:
            Validated and converted row

        Raises:
            ValueError: If validation fails in strict mode
        """
        validated_row = {}

        for field in field_schema:
            field_name = field.get("field_name")
            data_type = field.get("data_type", "string")

            if not field_name:
                continue

            # Get value from row
            value = row.get(field_name)

            # Apply type conversion
            try:
                converted_value = self._convert_value(value, data_type)
                validated_row[field_name] = converted_value
            except ValueError as e:
                if strict_validation:
                    error_msg = f"Row {row_index + 1}, field '{field_name}': {e}"
                    logger.error(f"[CustomInput] Validation error: {error_msg}")
                    raise ValueError(error_msg) from e
                # In non-strict mode, keep original value
                logger.warning(
                    f"[CustomInput] Type conversion warning for row {row_index + 1}, "
                    f"field '{field_name}': {e}. Keeping original value."
                )
                validated_row[field_name] = value

        return validated_row

    def load_data(self) -> list[Data]:
        """Load custom data and return as list of Data objects.

        Returns:
            List of Data objects containing validated data
        """
        logger.info("[CustomInput] load_data called")

        try:
            # Get field schema
            field_schema = getattr(self, "field_schema", [])

            if not field_schema:
                logger.warning("[CustomInput] No field schema defined, returning empty sample")
                # Return empty sample for field inference
                return [Data(data={})]

            # Get data table
            data_table = getattr(self, "data_table", [])

            if not data_table:
                logger.warning("[CustomInput] No data rows, returning sample record with schema")
                # Create sample record with None values for field inference
                sample_data = {field.get("field_name"): None for field in field_schema if field.get("field_name")}
                return [Data(data=sample_data)]

            # Get strict validation setting
            strict_validation = getattr(self, "strict_validation", True)

            # Validate and convert all rows
            result = []
            for idx, row in enumerate(data_table):
                try:
                    validated_row = self._validate_data_row(row, field_schema, strict_validation, idx)
                    result.append(Data(data=validated_row))
                except Exception as e:
                    error_msg = f"Row {idx + 1} validation failed: {e}"
                    logger.error(f"[CustomInput] {error_msg}")
                    raise ValueError(error_msg) from e

            self.status = _format_i18n("components.input_output.custom_input.status.data_loaded", count=len(result))
            logger.info(f"[CustomInput] Loaded {len(result)} data rows")

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[CustomInput] Failed to load data: {error_msg}")
            logger.exception("[CustomInput] Full exception traceback:")

            translated_msg = _format_i18n(
                "components.input_output.custom_input.errors.validation_failed", error=error_msg
            )
            raise ValueError(translated_msg) from e
