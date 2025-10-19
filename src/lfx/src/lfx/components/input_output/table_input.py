from typing import Any

import i18n
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from lfx.base.datasource.manager import DataSourceManager
from lfx.base.transformation import TransformationExecutor
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, MultilineInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Transformation rule options - just the values
TRANSFORMATION_RULE_VALUES = [
    "none",
    "upper",
    "lower",
    "trim",
    "mask_phone",
    "mask_idcard",
    "mask_email",
    "mask_name",
    "md5",
    "sha256",
    "to_int",
    "to_float",
    "to_str",
    "to_bool",
    "expression",
    "javascript",
    "python",
]


class ETLTableInputComponent(Component):
    display_name = i18n.t("components.input_output.table_input.display_name")
    description = i18n.t("components.input_output.table_input.description")
    icon = "database"
    name = "ETLTableInput"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.datasource_manager = DataSourceManager()
        self.transformation_executor = TransformationExecutor()

    inputs = [
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.table_input.datasource_selector.display_name"),
            info=i18n.t("components.input_output.table_input.datasource_selector.info"),
            required=True,
            refresh_button=True,
            options=[],  # Will be loaded dynamically
            real_time_refresh=True,
            action_button={
                "label": i18n.t("dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
        ),
        MultilineInput(
            name="sql_query",
            display_name=i18n.t("components.input_output.table_input.sql_query.display_name"),
            info=i18n.t("components.input_output.table_input.sql_query.info"),
            required=True,
            placeholder="SELECT * FROM your_table WHERE 1=1",
            advanced=False,
        ),
        TableInput(
            name="field_mappings",
            display_name=i18n.t("components.input_output.table_input.field_mappings.display_name"),
            info=i18n.t("components.input_output.table_input.field_mappings.info"),
            table_schema=[
                {
                    "name": "source_field",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.source_field"),
                    "type": "str",
                    "disable_edit": True,  # 只读
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.data_type"),
                    "type": "str",
                    "disable_edit": True,  # 只读
                },
                {
                    "name": "null_value",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.null_value"),
                    "type": "str",
                    "description": i18n.t("components.input_output.table_input.field_mappings.null_value_desc"),
                },
                {
                    "name": "transformation_rule",
                    "display_name": i18n.t("components.input_output.table_input.field_mappings.transformation_rule"),
                    "type": "str",
                    "formatter": "text",
                    "options": TRANSFORMATION_RULE_VALUES,
                },
            ],
            value=[],
            table_options={
                "block_add": True,
                "block_delete": True,
                "action_buttons": [
                    {
                        "name": "analyze_sql",
                        "label": i18n.t("components.input_output.table_input.field_mappings.analyze_sql_button"),
                        "icon": "Search",
                        "position": "top",
                    }
                ],
            },
            advanced=False,
        ),
        BoolInput(
            name="use_pagination",
            display_name=i18n.t("components.input_output.table_input.use_pagination.display_name"),
            info=i18n.t("components.input_output.table_input.use_pagination.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="page_size",
            display_name=i18n.t("components.input_output.table_input.page_size.display_name"),
            info=i18n.t("components.input_output.table_input.page_size.info"),
            value=1000,
            range_spec={"min": 1, "max": 100000},
            advanced=True,
        ),
        IntInput(
            name="max_records",
            display_name=i18n.t("components.input_output.table_input.max_records.display_name"),
            info=i18n.t("components.input_output.table_input.max_records.info"),
            value=0,
            advanced=True,
        ),
        BoolInput(
            name="enable_transaction",
            display_name=i18n.t("components.input_output.table_input.enable_transaction.display_name"),
            info=i18n.t("components.input_output.table_input.enable_transaction.info"),
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="isolation_level",
            display_name=i18n.t("components.input_output.table_input.isolation_level.display_name"),
            info=i18n.t("components.input_output.table_input.isolation_level.info"),
            options=["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE", "DEFAULT"],
            value="DEFAULT",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="data", display_name="Data", method="load_data"),
        Output(name="row_count", display_name="Row Count", method="get_row_count"),
        Output(name="fields_schema", display_name="Fields Schema", method="get_fields_schema"),
    ]

    def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates based on field changes and action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(
            f"[TableInput] update_build_config called - field_name: {field_name}, field_value: {field_value}, action: {action}"
        )

        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        # Always load datasources for: initial load (None) or refresh datasource_selector (empty value)
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug(f"[TableInput] Loading datasources (field_name={field_name}, field_value={field_value})")
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{api_url}/api/v1/datasources")

                    if response.status_code == 200:
                        datasources = response.json()
                        logger.debug(f"[TableInput] Loaded {len(datasources)} datasources from API")

                        # 构建显示选项和元数据
                        options = []
                        options_metadata = []

                        for ds in datasources:
                            display_name = f"{ds['name']} ({ds['type']})"
                            options.append(display_name)
                            # 使用 options_metadata 存储 ID 映射
                            options_metadata.append({"id": ds["id"], "name": ds["name"], "type": ds["type"]})

                        build_config["datasource_selector"]["options"] = options
                        build_config["datasource_selector"]["options_metadata"] = options_metadata
                        logger.debug(f"[TableInput] Set datasource_selector options: {options}")
                        logger.debug(f"[TableInput] Set options_metadata with {len(options_metadata)} entries")
                    else:
                        logger.warning(f"[TableInput] Failed to load datasources, status: {response.status_code}")
            except Exception as e:
                logger.error(f"[TableInput] Error loading datasources: {e}")

        # When datasource is selected, we can optionally load table/column metadata for SQL assistance
        # But we don't auto-populate anything - user writes their own SQL
        if field_name == "datasource_selector" and field_value:
            current_datasource = field_value
            logger.debug(f"[TableInput] Datasource selected: {current_datasource}")
            # Just log the selection, no further action needed
            # User will write their own SQL query

        # Handle action button clicks (from field_mappings table)
        if field_name == "field_mappings" and action == "analyze_sql":
            logger.info("[TableInput] SQL analysis triggered by action button")

            try:
                # 获取当前SQL和数据源
                current_sql = build_config.get("sql_query", {}).get("value")
                current_datasource = build_config.get("datasource_selector", {}).get("value")

                if not current_sql:
                    logger.warning("[TableInput] No SQL query provided")
                    self.status = i18n.t("components.input_output.table_input.errors.no_sql")
                    return build_config

                if not current_datasource:
                    logger.warning("[TableInput] No datasource selected")
                    self.status = i18n.t("components.input_output.table_input.errors.no_datasource")
                    return build_config

                # 从 options_metadata 中获取数据源ID
                datasource_id = self._get_datasource_id_from_metadata(
                    current_datasource, build_config.get("datasource_selector", {}).get("options_metadata", [])
                )

                if not datasource_id:
                    logger.error(f"[TableInput] Cannot find datasource ID for: {current_datasource}")
                    self.status = i18n.t("components.input_output.table_input.errors.no_datasource")
                    return build_config

                # 执行SQL分析
                logger.info("[TableInput] Starting SQL field inference...")
                self.status = i18n.t("components.input_output.table_input.status.analyzing_sql")

                field_info = self._infer_field_info(datasource_id, current_sql)

                if field_info:
                    # 更新field_mappings
                    build_config["field_mappings"]["value"] = field_info
                    logger.info(f"[TableInput] SQL analysis completed, generated {len(field_info)} field mappings")
                    self.status = i18n.t(
                        "components.input_output.table_input.status.analysis_success", count=len(field_info)
                    )
                else:
                    logger.warning("[TableInput] No fields inferred from SQL")
                    self.status = i18n.t("components.input_output.table_input.status.no_fields_found")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[TableInput] SQL analysis failed: {error_msg}")
                self.status = i18n.t("components.input_output.table_input.errors.analysis_failed", error=error_msg)
                # 不抛出异常，让用户可以继续操作

        logger.debug(f"[TableInput] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _get_datasource_id_from_metadata(self, display_name: str, options_metadata: list[dict]) -> str | None:
        """从 options_metadata 中根据显示名称获取数据源ID"""
        for metadata in options_metadata:
            # 重建显示名称并匹配
            meta_display_name = f"{metadata.get('name')} ({metadata.get('type')})"
            if meta_display_name == display_name:
                datasource_id = metadata.get("id")
                logger.debug(f"[TableInput] Found datasource ID '{datasource_id}' for display name '{display_name}'")
                return datasource_id

        logger.warning(f"[TableInput] No metadata found for display name: {display_name}")
        return None

    def _parse_sql_fields(self, sql: str) -> list[str]:
        """从SQL中解析字段名"""
        import sqlparse

        try:
            # 解析SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                logger.warning("[TableInput] SQL parsing returned empty result")
                return []

            stmt = parsed[0]
            fields = []
            in_select = False

            for token in stmt.tokens:
                # 跳过空白和注释
                if token.is_whitespace or isinstance(token, sqlparse.sql.Comment):
                    continue

                # 找到SELECT关键字
                if token.ttype is sqlparse.tokens.Keyword.DML and token.value.upper() == "SELECT":
                    in_select = True
                    continue

                # 遇到FROM等关键字，停止解析
                if in_select and token.ttype is sqlparse.tokens.Keyword:
                    break

                if in_select:
                    # 处理IdentifierList (多个字段，逗号分隔)
                    if isinstance(token, sqlparse.sql.IdentifierList):
                        for identifier in token.get_identifiers():
                            field_name = self._extract_field_name(identifier)
                            if field_name and field_name != "*":
                                fields.append(field_name)
                            elif field_name == "*":
                                return ["*"]  # 特殊标记
                    # 处理单个Identifier
                    elif isinstance(token, sqlparse.sql.Identifier):
                        field_name = self._extract_field_name(token)
                        if field_name:
                            fields.append(field_name)
                    # 处理通配符 *
                    elif token.ttype is sqlparse.tokens.Wildcard:
                        return ["*"]

            logger.debug(f"[TableInput] Parsed fields from SQL: {fields}")
            return fields

        except Exception as e:
            logger.error(f"[TableInput] SQL parsing error: {e}")
            return []

    def _extract_field_name(self, identifier) -> str:
        """提取字段名（处理别名）"""
        try:
            # 如果有别名(AS)，使用别名
            if identifier.has_alias():
                alias = identifier.get_alias()
                logger.debug(f"[TableInput] Field has alias: {alias}")
                return alias

            # 否则使用真实名称
            real_name = identifier.get_real_name()

            # 处理函数调用，如 COUNT(*), MAX(id) 等
            if identifier.ttype is None and "(" in str(identifier):
                # 尝试提取函数表达式作为字段名
                return str(identifier).strip()

            return real_name
        except Exception as e:
            logger.error(f"[TableInput] Error extracting field name: {e}")
            return str(identifier).strip()

    def _get_connection_string(self, datasource_id: str) -> str:
        """获取数据源连接字符串"""
        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/connection-string")

                if response.status_code != 200:
                    raise ValueError(f"Failed to get connection string, status: {response.status_code}")

                connection_data = response.json()
                connection_string = connection_data.get("connection_string")

                if not connection_string:
                    raise ValueError("Connection string is empty")

                return connection_string
        except Exception as e:
            logger.error(f"[TableInput] Error getting connection string: {e}")
            raise

    def _map_dtype(self, dtype) -> str:
        """映射pandas dtype到标准类型"""
        if pd.api.types.is_integer_dtype(dtype):
            return "integer"
        if pd.api.types.is_float_dtype(dtype):
            return "float"
        if pd.api.types.is_bool_dtype(dtype):
            return "boolean"
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "datetime"
        if pd.api.types.is_object_dtype(dtype):
            return "string"
        return "string"

    def _infer_field_info(self, datasource_id: str, sql: str) -> list[dict]:
        """解析SQL并推断字段信息（执行LIMIT 1查询）"""
        try:
            # 1. 解析SQL字段
            logger.debug(f"[TableInput] Parsing SQL: {sql[:100]}...")
            fields = self._parse_sql_fields(sql)

            if not fields:
                logger.warning("[TableInput] No fields parsed from SQL")
                return []

            # 2. 获取数据库连接
            connection_string = self._get_connection_string(datasource_id)
            engine = create_engine(connection_string, poolclass=NullPool)

            field_info = []

            try:
                with engine.connect() as conn:
                    # 3. 如果是 *, 需要执行查询获取实际列名
                    if fields == ["*"]:
                        logger.debug("[TableInput] Wildcard detected, executing LIMIT 0 to get columns")
                        df = pd.read_sql_query(text(f"{sql} LIMIT 0"), conn)
                        fields = df.columns.tolist()
                        logger.debug(f"[TableInput] Actual columns: {fields}")

                    # 4. 执行 LIMIT 1 获取样本数据，推断类型
                    logger.debug("[TableInput] Executing LIMIT 1 to infer types")
                    df_sample = pd.read_sql_query(text(f"{sql} LIMIT 1"), conn)

                    # 5. 为每个字段创建映射配置
                    for field in fields:
                        if field in df_sample.columns:
                            dtype = df_sample[field].dtype
                            data_type = self._map_dtype(dtype)
                        else:
                            # 字段不在结果中（可能是别名问题），默认string
                            data_type = "string"

                        field_info.append(
                            {
                                "source_field": field,
                                "data_type": data_type,
                                "null_value": "",
                                "transformation_rule": "none",
                            }
                        )

                    logger.info(f"[TableInput] Inferred {len(field_info)} fields")
                    return field_info

            finally:
                engine.dispose()

        except Exception as e:
            logger.error(f"[TableInput] Field inference failed: {e}")
            raise

    def _get_datasource_id(self) -> str:
        """从选中的显示名称获取实际的数据源ID（运行时从API获取）"""
        if not self.datasource_selector:
            raise ValueError("No datasource selected")

        import os

        import httpx

        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources")
                if response.status_code == 200:
                    datasources = response.json()

                    # 遍历所有数据源，找到匹配的显示名称
                    for ds in datasources:
                        display_name = f"{ds['name']} ({ds['type']})"
                        if display_name == self.datasource_selector:
                            datasource_id = ds["id"]
                            logger.debug(
                                f"[TableInput] Found datasource ID '{datasource_id}' for '{self.datasource_selector}'"
                            )
                            return datasource_id

                    # 如果没找到匹配的显示名称，尝试直接使用作为ID（向后兼容）
                    logger.warning(
                        f"[TableInput] Display name '{self.datasource_selector}' not found, trying as direct ID"
                    )
                    return self.datasource_selector

                logger.error(f"[TableInput] Failed to load datasources from API, status: {response.status_code}")
                raise ValueError(f"Failed to load datasources: HTTP {response.status_code}")

        except httpx.HTTPError as e:
            logger.error(f"[TableInput] HTTP error when fetching datasources: {e}")
            raise ValueError(f"Failed to fetch datasources: {e}")

        except Exception as e:
            logger.error(f"[TableInput] Unexpected error: {e}")
            raise ValueError(f"Cannot determine datasource ID: {e}")

    def _apply_null_values(self, row_dict: dict) -> dict:
        """应用缺省值填充空值字段"""
        if not self.field_mappings:
            return row_dict

        result = {}

        for mapping in self.field_mappings:
            source_field = mapping.get("source_field")
            null_value = mapping.get("null_value", "")

            if source_field and source_field in row_dict:
                value = row_dict[source_field]

                # 检查是否为空值：None, "", NaN
                is_null = value is None or value == "" or (isinstance(value, float) and pd.isna(value))

                if is_null and null_value:
                    # 使用缺省值
                    result[source_field] = null_value
                    logger.debug(f"[TableInput] Applied null value for '{source_field}': '{null_value}'")
                else:
                    result[source_field] = value
            elif source_field:
                # 字段在映射中但不在数据中
                result[source_field] = row_dict.get(source_field)

        # 保留未映射的字段
        for key, value in row_dict.items():
            if key not in result:
                result[key] = value

        return result

    def _apply_field_transformations(self, row_dict: dict) -> dict:
        if not self.field_mappings:
            return row_dict

        result = {}

        for mapping in self.field_mappings:
            source_field = mapping.get("source_field")
            transformation_rule = mapping.get("transformation_rule", None)

            if source_field and source_field in row_dict:
                value = row_dict[source_field]

                # 应用转换规则
                if transformation_rule and transformation_rule != "none":
                    try:
                        value = self.transformation_executor.apply_transformation(value, transformation_rule, row_dict)
                        logger.debug(f"[TableInput] Applied transformation '{transformation_rule}' to '{source_field}'")
                    except Exception as e:
                        logger.error(f"[TableInput] Transformation failed for '{source_field}': {e}")

                result[source_field] = value

        # 保留未映射的字段
        for key, value in row_dict.items():
            mapped_sources = [m.get("source_field") for m in self.field_mappings]
            if key not in mapped_sources and key not in result:
                result[key] = value

        return result

    def load_data(self) -> list[Data]:
        """Extract data from database table with SQL support, pagination, and transaction handling."""
        try:
            logger.info("[TableInput] load_data called")
            self.status = i18n.t("components.input_output.table_input.status.connecting")

            # Validate inputs
            if not self.datasource_selector or not self.sql_query:
                logger.warning("[TableInput] Missing datasource or SQL query")
                # In design-time context (e.g., field analysis), return empty sample with schema
                if self.field_mappings:
                    # Use field_mappings to create a sample record
                    sample_data = {mapping.get("source_field"): None for mapping in self.field_mappings if mapping.get("source_field")}
                    if sample_data:
                        logger.info(f"[TableInput] Returning sample record with {len(sample_data)} fields from mappings")
                        return [Data(data=sample_data)]

                raise ValueError(i18n.t("components.input_output.table_input.errors.missing_config"))

            # 获取实际的数据源ID(从显示名称转换)
            datasource_id = self._get_datasource_id()
            logger.debug(f"[TableInput] Using datasource ID: {datasource_id}")

            # Get connection string from datasource API
            import os

            import httpx

            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}/connection-string")

                    if response.status_code != 200:
                        logger.error(f"[TableInput] Failed to get connection string, status: {response.status_code}")
                        raise ValueError(i18n.t("components.input_output.table_input.errors.invalid_datasource"))

                    connection_data = response.json()
                    connection_string = connection_data.get("connection_string")

                    if not connection_string:
                        logger.error("[TableInput] Connection string is empty")
                        raise ValueError(i18n.t("components.input_output.table_input.errors.invalid_datasource"))

            except httpx.RequestError as e:
                logger.error(f"[TableInput] HTTP request failed: {e}")
                # In design-time, if API is not available, use field_mappings as fallback
                if self.field_mappings:
                    sample_data = {mapping.get("source_field"): None for mapping in self.field_mappings if mapping.get("source_field")}
                    if sample_data:
                        logger.info(f"[TableInput] API unavailable, returning sample record with {len(sample_data)} fields from mappings")
                        return [Data(data=sample_data)]
                raise ValueError(f"Failed to connect to datasource API: {e}") from e

            # Build SQL query - use as provided by user
            sql_query = self.sql_query.strip()

            # Create database engine
            engine = create_engine(
                connection_string,
                poolclass=NullPool,
                isolation_level=self.isolation_level if self.isolation_level != "DEFAULT" else None,
            )

            result_data = []
            total_records = 0

            with engine.connect() as connection:
                # Start transaction if enabled
                if self.enable_transaction:
                    trans = connection.begin()
                    try:
                        result_data = self._fetch_data(connection, sql_query)
                        trans.commit()
                    except Exception as e:
                        trans.rollback()
                        raise e
                else:
                    result_data = self._fetch_data(connection, sql_query)

            total_records = len(result_data)

            # IMPORTANT: Ensure we return at least one sample record for field inference
            # If no data was returned but query succeeded, create a sample record with NULL values
            if not result_data:
                logger.warning("[TableInput] No data returned from query, creating sample record for field inference")
                # Get schema from LIMIT 1 to create empty sample
                with engine.connect() as connection:
                    df_sample = pd.read_sql_query(text(f"{sql_query} LIMIT 0"), connection)
                    if not df_sample.empty or len(df_sample.columns) > 0:
                        # Create a sample record with None values for all fields
                        sample_data = {col: None for col in df_sample.columns}
                        result_data = [Data(data=sample_data)]
                        logger.info(f"[TableInput] Created sample record with {len(sample_data)} fields")

            self.status = i18n.t("components.input_output.table_input.status.success", records=total_records)
            logger.info(f"[TableInput] Returning {len(result_data)} data records")

            return result_data

        except Exception as e:
            # Improved error logging
            logger.exception(f"[TableInput] load_data failed with error: {e}")
            error_msg = str(e)

            # Try to use i18n, but fallback to plain error if i18n fails
            try:
                status_msg = i18n.t("components.input_output.table_input.errors.extraction_failed", error=error_msg)
            except Exception:
                status_msg = f"Data extraction failed: {error_msg}"

            self.status = status_msg
            raise ValueError(status_msg) from e

    def _fetch_data(self, connection, sql_query: str) -> list[Data]:
        """Fetch data with pagination support and transformation."""
        result_data = []

        if self.use_pagination:
            offset = 0
            while True:
                # Apply pagination to query
                paginated_query = f"{sql_query} LIMIT {self.page_size} OFFSET {offset}"

                df = pd.read_sql_query(text(paginated_query), connection)

                if df.empty:
                    break

                # Convert DataFrame to Data objects with transformations
                for _, row in df.iterrows():
                    row_dict = row.to_dict()

                    # 1. 应用缺省值填充
                    if self.field_mappings:
                        row_dict = self._apply_null_values(row_dict)

                    # 2. 应用字段转换规则
                    if self.field_mappings:
                        row_dict = self._apply_field_transformations(row_dict)

                    result_data.append(Data(data=row_dict))

                offset += self.page_size

                # Check max records limit
                if self.max_records > 0 and len(result_data) >= self.max_records:
                    result_data = result_data[: self.max_records]
                    break
        else:
            # Fetch all data at once
            df = pd.read_sql_query(text(sql_query), connection)

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # 1. 应用缺省值填充
                if self.field_mappings:
                    row_dict = self._apply_null_values(row_dict)

                # 2. 应用字段转换规则
                if self.field_mappings:
                    row_dict = self._apply_field_transformations(row_dict)

                result_data.append(Data(data=row_dict))

                if self.max_records > 0 and len(result_data) >= self.max_records:
                    break

        return result_data

    def get_row_count(self) -> Data:
        """Get the count of extracted rows."""
        data = self.load_data()
        count = len(data)
        return Data(data={"row_count": count, "datasource": self.datasource_selector})

    def get_fields_schema(self) -> Data:
        """Get the schema (field names and types) from the SQL query result.

        This method is designed to be lightweight - it only fetches 1 row to infer schema.
        This is useful for downstream components that need to know field structure
        without loading all data.

        Returns:
            Data: A Data object containing fields metadata with structure:
                  {
                      "fields": [
                          {"name": "field1", "type": "string"},
                          {"name": "field2", "type": "integer"},
                          ...
                      ],
                      "field_names": ["field1", "field2", ...]  # For quick access
                  }
        """
        try:
            logger.info("[TableInput] get_fields_schema called")

            # Reuse existing field_mappings if available (from SQL analysis)
            if self.field_mappings:
                logger.debug(f"[TableInput] Using existing field_mappings: {len(self.field_mappings)} fields")

                fields = [
                    {
                        "name": mapping.get("source_field"),
                        "type": mapping.get("data_type", "string"),
                    }
                    for mapping in self.field_mappings
                    if mapping.get("source_field")
                ]

                field_names = [f["name"] for f in fields]

                logger.info(f"[TableInput] Returning schema with {len(fields)} fields from mappings")
                return Data(data={"fields": fields, "field_names": field_names})

            # If no field_mappings, infer from actual data (fetch LIMIT 1)
            logger.debug("[TableInput] No field_mappings available, inferring from data")

            # Get datasource ID
            datasource_id = self._get_datasource_id()

            # Get connection string
            connection_string = self._get_connection_string(datasource_id)
            engine = create_engine(connection_string, poolclass=NullPool)

            try:
                with engine.connect() as connection:
                    # Execute LIMIT 1 to get schema
                    sql_query = self.sql_query.strip()
                    df_sample = pd.read_sql_query(text(f"{sql_query} LIMIT 1"), connection)

                    fields = []
                    for col in df_sample.columns:
                        dtype = df_sample[col].dtype
                        data_type = self._map_dtype(dtype)
                        fields.append({"name": col, "type": data_type})

                    field_names = [f["name"] for f in fields]

                    logger.info(f"[TableInput] Inferred schema with {len(fields)} fields from data")
                    return Data(data={"fields": fields, "field_names": field_names})

            finally:
                engine.dispose()

        except Exception as e:
            logger.error(f"[TableInput] Failed to get fields schema: {e}")
            # Return empty schema rather than failing
            return Data(data={"fields": [], "field_names": []})
