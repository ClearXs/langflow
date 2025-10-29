import base64
from typing import Any

import i18n
import pandas as pd
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, Output, SecretStrInput, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLDataEncryptionComponent(Component):
    display_name = i18n.t("components.security.data_encryption.display_name")
    description = i18n.t("components.security.data_encryption.description")
    icon = "lock"
    name = "ETLDataEncryption"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.security.data_encryption.data_input.display_name"),
            info=i18n.t("components.security.data_encryption.data_input.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="operation",
            display_name=i18n.t("components.security.data_encryption.operation.display_name"),
            info=i18n.t("components.security.data_encryption.operation.info"),
            options=["encrypt", "decrypt"],
            options_metadata=[
                {
                    "value": "encrypt",
                    "label": i18n.t("components.security.data_encryption.operation.types.encrypt"),
                },
                {
                    "value": "decrypt",
                    "label": i18n.t("components.security.data_encryption.operation.types.decrypt"),
                },
            ],
            value="encrypt",
        ),
        SecretStrInput(
            name="encryption_key",
            display_name=i18n.t("components.security.data_encryption.encryption_key.display_name"),
            info=i18n.t("components.security.data_encryption.encryption_key.info"),
            required=True,
        ),
        TableInput(
            name="field_configs",
            display_name=i18n.t("components.security.data_encryption.field_configs.display_name"),
            info=i18n.t("components.security.data_encryption.field_configs.info"),
            table_schema=[
                {
                    "name": "field",
                    "display_name": i18n.t("components.security.data_encryption.field_configs.field"),
                    "type": "str",
                    "formatter": "dropdown",
                    "options": [],  # 动态填充
                    "required": True,
                    "description": i18n.t("components.security.data_encryption.field_configs.field_desc"),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.security.data_encryption.field_configs.load_fields_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        BoolInput(
            name="use_base64",
            display_name=i18n.t("components.security.data_encryption.use_base64.display_name"),
            info=i18n.t("components.security.data_encryption.use_base64.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.security.data_encryption.outputs.data.display_name"),
            method="process_encryption",
        ),
        Output(
            name="encryption_stats",
            display_name=i18n.t("components.security.data_encryption.outputs.encryption_stats.display_name"),
            method="get_encryption_stats",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates for field loading.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[DataEncryption] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle "load_fields" button click
        if field_name == "field_configs" and action == "load_fields":
            logger.info("[DataEncryption] Field loading triggered")

            try:
                # Get graph_data and node_id from build_config
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[DataEncryption] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[DataEncryption] No graph data available")
                    self.status = i18n.t("components.security.data_encryption.errors.no_graph_data")
                    return build_config

                # Fetch upstream data
                upstream_data = await self.get_upstream_data(
                    input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                )

                if not upstream_data:
                    logger.warning("[DataEncryption] No data returned from upstream node")
                    self.status = i18n.t("components.security.data_encryption.status.no_fields_found")
                    return build_config

                # Extract field names
                field_names = self._extract_field_names(upstream_data)

                if not field_names:
                    logger.warning("[DataEncryption] No fields extracted from upstream data")
                    self.status = i18n.t("components.security.data_encryption.status.no_fields_found")
                    return build_config

                # Update dropdown options for field column
                build_config["field_configs"]["table_schema"][0]["options"] = field_names

                # Auto-fill table with default encryption configs if empty
                if not build_config["field_configs"].get("value"):
                    build_config["field_configs"]["value"] = [{"field": name} for name in field_names]
                    logger.info(f"[DataEncryption] Auto-filled {len(field_names)} field encryption configs")
                else:
                    # Just update the options, keep existing rows
                    logger.info(f"[DataEncryption] Updated field options with {len(field_names)} fields")

                self.status = i18n.t("components.security.data_encryption.status.load_success", count=len(field_names))

            except ValueError as e:
                error_msg = str(e)
                logger.warning(f"[DataEncryption] Field loading warning: {error_msg}")

                # Fallback: try to extract fields from upstream node config
                try:
                    logger.info("[DataEncryption] Attempting fallback: extracting fields from upstream node config")
                    field_names = self._extract_fields_from_upstream_config(build_config, graph_data, node_id)

                    if field_names:
                        # Update dropdown options for field column
                        build_config["field_configs"]["table_schema"][0]["options"] = field_names

                        # Auto-fill table with default encryption configs if empty
                        if not build_config["field_configs"].get("value"):
                            build_config["field_configs"]["value"] = [{"field": name} for name in field_names]
                            logger.info(
                                f"[DataEncryption] Auto-filled {len(field_names)} field encryption configs (from config)"
                            )
                        else:
                            logger.info(
                                f"[DataEncryption] Updated field options with {len(field_names)} fields (from config)"
                            )

                        self.status = i18n.t(
                            "components.security.data_encryption.status.load_success", count=len(field_names)
                        )
                    else:
                        self.status = i18n.t("components.security.data_encryption.errors.load_failed", error=error_msg)
                except Exception:  # noqa: BLE001
                    logger.exception("[DataEncryption] Fallback also failed")
                    self.status = i18n.t("components.security.data_encryption.errors.load_failed", error=error_msg)

            except Exception:  # noqa: BLE001
                logger.exception("[DataEncryption] Field loading failed with unexpected error")
                self.status = i18n.t("components.security.data_encryption.errors.graph_not_available")

        return build_config

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """Extract field names from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field names
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
                logger.warning(f"[DataEncryption] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[DataEncryption] Expected dict, got {type(data_dict)}")
                return []

            field_names = list(data_dict.keys())
            logger.debug(f"[DataEncryption] Extracted {len(field_names)} field names: {field_names}")
            return field_names

        except Exception:  # noqa: BLE001
            logger.exception("[DataEncryption] Failed to extract field names")
            return []

    def _extract_fields_from_upstream_config(self, build_config: dict, graph_data: dict, node_id: str) -> list[str]:
        """Extract field names from upstream node configuration.

        This is a fallback method when upstream node cannot be executed.
        It tries to extract field information from the upstream node's configuration.

        Args:
            build_config: Current build configuration
            graph_data: Flow graph data
            node_id: Current node ID

        Returns:
            List of field names extracted from upstream config
        """
        try:
            from lfx.custom.graph_utils import find_upstream_node_id

            # Find upstream node
            upstream_node_id = find_upstream_node_id(graph_data, node_id, "data_input")
            if not upstream_node_id:
                logger.warning("[DataEncryption] No upstream node found")
                return []

            # Find upstream node in graph_data
            nodes = graph_data.get("nodes", [])
            upstream_node = None
            for node in nodes:
                if node.get("id") == upstream_node_id:
                    upstream_node = node
                    break

            if not upstream_node:
                logger.warning(f"[DataEncryption] Upstream node {upstream_node_id} not found in graph data")
                return []

            upstream_node_data = upstream_node.get("data", {})
            upstream_node_type = upstream_node_data.get("type")

            logger.info(f"[DataEncryption] Upstream node type: {upstream_node_type}")

            # Extract fields based on upstream node type
            field_names = []

            # For encryption/masking components, extract from field_configs
            if upstream_node_type in ["ETLDataEncryption", "ETLDataMasking"]:
                # Look for field_configs or masking_rules in node data
                node_config = upstream_node_data.get("node", {})

                # The actual config values are stored in the 'template' section
                template = node_config.get("template", {})

                # Try field_configs (encryption component)
                if "field_configs" in template:
                    field_configs = template.get("field_configs", {})
                    if isinstance(field_configs, dict):
                        config_value = field_configs.get("value", [])
                        if isinstance(config_value, list):
                            field_names = [
                                config.get("field")
                                for config in config_value
                                if isinstance(config, dict) and config.get("field")
                            ]

                # Try masking_rules (masking component)
                if not field_names and "masking_rules" in template:
                    masking_rules = template.get("masking_rules", {})
                    if isinstance(masking_rules, dict):
                        config_value = masking_rules.get("value", [])
                        if isinstance(config_value, list):
                            field_names = [
                                config.get("field")
                                for config in config_value
                                if isinstance(config, dict) and config.get("field")
                            ]

            # For table components or other data sources
            elif upstream_node_type in ["ETLTableInput", "ETLCustomInput", "ETLCSVInput", "ETLExcelInput"]:
                node_config = upstream_node_data.get("node", {})
                template = node_config.get("template", {})

                # Try to get from table_schema
                if "table_schema" in template:
                    table_schema = template.get("table_schema", {})
                    if isinstance(table_schema, dict):
                        schema_value = table_schema.get("value", [])
                        if isinstance(schema_value, list):
                            field_names = [
                                schema.get("field_name")
                                for schema in schema_value
                                if isinstance(schema, dict) and schema.get("field_name")
                            ]

                # Try to get from table_data
                if not field_names and "table_data" in template:
                    table_data = template.get("table_data", {})
                    if isinstance(table_data, dict):
                        data_value = table_data.get("value", [])
                        if isinstance(data_value, list) and len(data_value) > 0:
                            # Extract keys from first row
                            first_row = data_value[0]
                            if isinstance(first_row, dict):
                                field_names = list(first_row.keys())

            if field_names:
                logger.info(f"[DataEncryption] Extracted {len(field_names)} fields from upstream config: {field_names}")
            else:
                logger.warning("[DataEncryption] No fields found in upstream config")

            return field_names

        except Exception:  # noqa: BLE001
            logger.exception("[DataEncryption] Failed to extract fields from upstream config")
            return []

    def process_encryption(self) -> list[Data]:
        """Apply encryption/decryption to specified fields."""
        try:
            logger.info(f"[DataEncryption] Starting {self.operation}")

            if not self.data_input or not self.field_configs or not self.encryption_key:
                raise ValueError(i18n.t("components.security.data_encryption.errors.missing_config"))

            # Convert to DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            logger.info(
                f"[DataEncryption] Processing {len(df)} records with {len(self.field_configs)} field configurations"
            )

            cipher = self._get_cipher()

            for config in self.field_configs:
                field = config.get("field", "").strip()

                if not field:
                    logger.warning(f"[DataEncryption] Skipping empty field config: {config}")
                    continue

                if field not in df.columns:
                    logger.warning(f"[DataEncryption] Field '{field}' not found in data, skipping")
                    continue

                logger.debug(f"[DataEncryption] Applying {self.operation} to field '{field}'")

                if self.operation == "encrypt":
                    df[field] = df[field].apply(lambda x: self._encrypt_value(str(x), cipher) if pd.notnull(x) else x)
                else:
                    df[field] = df[field].apply(lambda x: self._decrypt_value(str(x), cipher) if pd.notnull(x) else x)

            # Convert back to Data objects
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]

            self.status = i18n.t(
                "components.security.data_encryption.status.success",
                operation=self.operation,
                count=len(result),
                fields=len(self.field_configs),
            )

            logger.info(f"[DataEncryption] Successfully processed {len(result)} records")
            return result

        except ValueError:
            # Re-raise ValueError directly
            raise
        except Exception as e:
            error_msg = i18n.t("components.security.data_encryption.errors.process_failed", error=str(e))
            logger.exception(f"[DataEncryption] {error_msg}")
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _get_cipher(self):
        key_bytes = self.encryption_key.encode()
        if len(key_bytes) != 32:
            from cryptography.hazmat.backends import default_backend

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"langflow_etl_salt",
                iterations=100000,
                backend=default_backend(),
            )
            key_bytes = kdf.derive(key_bytes)
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)

    def _encrypt_value(self, value: str, cipher) -> str:
        encrypted = cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode() if self.use_base64 else encrypted.decode()

    def _decrypt_value(self, value: str, cipher) -> str:
        encrypted_bytes = base64.b64decode(value) if self.use_base64 else value.encode()
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode()

    def get_encryption_stats(self) -> Data:
        """Get statistics about the encryption/decryption operation."""
        try:
            processed_data = self.process_encryption()

            stats = {
                "operation": self.operation,
                "total_records": len(self.data_input) if self.data_input else 0,
                "processed_records": len(processed_data),
                "field_configs": [{"field": config.get("field")} for config in self.field_configs],
                "total_fields_processed": len(self.field_configs),
                "use_base64": self.use_base64,
            }

            logger.info(f"[DataEncryption] Stats: {stats}")
            return Data(data=stats)

        except Exception as e:
            logger.error(f"[DataEncryption] Failed to get encryption stats: {e}")
            return Data(
                data={
                    "operation": self.operation if hasattr(self, "operation") else "unknown",
                    "total_records": 0,
                    "processed_records": 0,
                    "field_configs": [],
                    "total_fields_processed": 0,
                    "use_base64": self.use_base64 if hasattr(self, "use_base64") else True,
                    "error": str(e),
                }
            )
