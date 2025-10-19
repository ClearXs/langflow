"""Unit tests for ETLDualStreamJoinComponent."""

from unittest.mock import patch

import pytest

from lfx.components.operations.dual_stream_join import ETLDualStreamJoinComponent
from lfx.schema import Data


class TestETLDualStreamJoinComponent:
    """Test suite for Dual Stream Join component."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock translation function
        with patch("i18n.t", side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            pass

    # ==================== 测试组1: 组件初始化 ====================

    def test_component_initialization(self):
        """Test component initializes correctly."""
        component = ETLDualStreamJoinComponent()

        assert component.display_name is not None
        assert component.icon == "git-merge"
        assert component.name == "ETLDualStreamJoin"
        assert len(component.inputs) == 7
        assert len(component.outputs) == 3

    # ==================== 测试组2: 基础Join操作 ====================

    def test_inner_join_simple(self):
        """Test basic inner join with single condition."""
        left_data = [
            Data(data={"id": 1, "name": "Alice", "dept_id": 10}),
            Data(data={"id": 2, "name": "Bob", "dept_id": 20}),
            Data(data={"id": 3, "name": "Charlie", "dept_id": 10}),
        ]

        right_data = [
            Data(data={"dept_id": 10, "dept_name": "Sales"}),
            Data(data={"dept_id": 20, "dept_name": "Engineering"}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "dept_id", "operator": "=", "right_key": "dept_id"}],
        )

        result = component.join_streams()

        assert len(result) == 3  # All records match
        assert result[0].data["name"] == "Alice"
        assert result[0].data["dept_name"] == "Sales"
        assert result[1].data["name"] == "Bob"
        assert result[1].data["dept_name"] == "Engineering"

    def test_left_join(self):
        """Test left join preserves all left records."""
        left_data = [
            Data(data={"id": 1, "order_id": 101}),
            Data(data={"id": 2, "order_id": 102}),
            Data(data={"id": 3, "order_id": 103}),  # No match in right
        ]

        right_data = [
            Data(data={"order_id": 101, "amount": 100.0}),
            Data(data={"order_id": 102, "amount": 200.0}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="left",
            join_conditions=[{"left_key": "order_id", "operator": "=", "right_key": "order_id"}],
        )

        result = component.join_streams()

        assert len(result) == 3  # All left records preserved
        # Check the unmatched record has null values
        unmatched = [r for r in result if r.data["id"] == 3][0]
        # Amount should be None or NaN for unmatched record
        assert unmatched.data.get("amount") is None or str(unmatched.data.get("amount")) == "nan"

    def test_right_join(self):
        """Test right join preserves all right records."""
        left_data = [
            Data(data={"user_id": 1, "username": "alice"}),
            Data(data={"user_id": 2, "username": "bob"}),
        ]

        right_data = [
            Data(data={"user_id": 1, "email": "alice@example.com"}),
            Data(data={"user_id": 2, "email": "bob@example.com"}),
            Data(data={"user_id": 3, "email": "charlie@example.com"}),  # No match in left
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="right",
            join_conditions=[{"left_key": "user_id", "operator": "=", "right_key": "user_id"}],
        )

        result = component.join_streams()

        assert len(result) == 3  # All right records preserved

    def test_outer_join(self):
        """Test outer join preserves records from both sides."""
        left_data = [
            Data(data={"key": "A", "left_value": 1}),
            Data(data={"key": "B", "left_value": 2}),
        ]

        right_data = [
            Data(data={"key": "B", "right_value": 20}),
            Data(data={"key": "C", "right_value": 30}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="outer",
            join_conditions=[{"left_key": "key", "operator": "=", "right_key": "key"}],
        )

        result = component.join_streams()

        assert len(result) == 3  # A, B, C all present

    # ==================== 测试组3: 多条件Join ====================

    def test_multi_condition_join(self):
        """Test join with multiple conditions (AND logic)."""
        left_data = [
            Data(data={"year": 2024, "month": 1, "sales": 1000}),
            Data(data={"year": 2024, "month": 2, "sales": 1500}),
            Data(data={"year": 2023, "month": 1, "sales": 900}),
        ]

        right_data = [
            Data(data={"year": 2024, "month": 1, "target": 950}),
            Data(data={"year": 2024, "month": 2, "target": 1200}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[
                {"left_key": "year", "operator": "=", "right_key": "year"},
                {"left_key": "month", "operator": "=", "right_key": "month"},
            ],
        )

        result = component.join_streams()

        assert len(result) == 2  # Only 2024 records match both conditions

    # ==================== 测试组4: 不同操作符 ====================

    def test_not_equal_operator(self):
        """Test join with != operator."""
        left_data = [
            Data(data={"id": 1, "status": "active"}),
            Data(data={"id": 2, "status": "inactive"}),
        ]

        right_data = [
            Data(data={"id": 1, "filter_status": "inactive"}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[
                {"left_key": "id", "operator": "=", "right_key": "id"},
                {"left_key": "status", "operator": "!=", "right_key": "filter_status"},
            ],
        )

        result = component.join_streams()

        # Only id=1 with status != filter_status should match
        assert len(result) == 1
        assert result[0].data["status"] == "active"

    def test_greater_than_operator(self):
        """Test join with > operator."""
        left_data = [
            Data(data={"product": "A", "price": 100}),
            Data(data={"product": "B", "price": 200}),
            Data(data={"product": "C", "price": 50}),
        ]

        right_data = [
            Data(data={"threshold": 75}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[
                {"left_key": "price", "operator": ">", "right_key": "threshold"},
            ],
        )

        result = component.join_streams()

        # Products A and B have price > 75
        assert len(result) == 2

    def test_less_than_or_equal_operator(self):
        """Test join with <= operator."""
        left_data = [
            Data(data={"item": "X", "quantity": 10}),
            Data(data={"item": "Y", "quantity": 20}),
        ]

        right_data = [
            Data(data={"max_quantity": 15}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[
                {"left_key": "quantity", "operator": "<=", "right_key": "max_quantity"},
            ],
        )

        result = component.join_streams()

        # Only item X has quantity <= 15
        assert len(result) == 1
        assert result[0].data["item"] == "X"

    # ==================== 测试组5: 字段冲突处理 ====================

    def test_field_name_conflict_with_prefix(self):
        """Test field name conflicts are resolved with prefixes."""
        left_data = [
            Data(data={"id": 1, "name": "Left Name", "value": 100}),
        ]

        right_data = [
            Data(data={"id": 1, "name": "Right Name", "value": 200}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
            left_prefix="L",
            right_prefix="R",
        )

        result = component.join_streams()

        assert len(result) == 1
        # Check prefixes are applied to conflicting fields
        # Pandas uses suffix format: column_suffix
        assert "name_L" in result[0].data or "name_R" in result[0].data

    # ==================== 测试组6: 去重功能 ====================

    def test_drop_duplicates(self):
        """Test duplicate removal after join."""
        left_data = [
            Data(data={"category": "A", "value": 10}),
            Data(data={"category": "A", "value": 10}),  # Duplicate
        ]

        right_data = [
            Data(data={"category": "A", "description": "Category A"}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "category", "operator": "=", "right_key": "category"}],
            drop_duplicates=True,
        )

        result = component.join_streams()

        # Should have only 1 record after deduplication
        assert len(result) == 1

    # ==================== 测试组7: 边界情况 ====================

    def test_empty_left_stream(self):
        """Test behavior with empty left stream."""
        component = ETLDualStreamJoinComponent(
            left_stream=[],
            right_stream=[Data(data={"id": 1})],
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        result = component.join_streams()

        assert len(result) == 0

    def test_empty_right_stream(self):
        """Test behavior with empty right stream."""
        component = ETLDualStreamJoinComponent(
            left_stream=[Data(data={"id": 1})],
            right_stream=[],
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        result = component.join_streams()

        assert len(result) == 0

    def test_no_matching_records(self):
        """Test join with no matching records."""
        left_data = [Data(data={"id": 1})]
        right_data = [Data(data={"id": 2})]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        result = component.join_streams()

        assert len(result) == 0

    def test_large_dataset(self):
        """Test performance with larger datasets."""
        # Create 1000 records on each side
        left_data = [Data(data={"id": i, "left_val": i * 2}) for i in range(1000)]
        right_data = [Data(data={"id": i, "right_val": i * 3}) for i in range(500, 1500)]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        result = component.join_streams()

        # Should match ids 500-999 (500 records)
        assert len(result) == 500

    # ==================== 测试组8: 错误处理 ====================

    def test_missing_join_conditions(self):
        """Test error handling when join conditions are missing."""
        component = ETLDualStreamJoinComponent(
            left_stream=[Data(data={"id": 1})],
            right_stream=[Data(data={"id": 1})],
            join_type="inner",
            join_conditions=[],
        )

        with pytest.raises(ValueError):
            component.join_streams()

    def test_missing_left_stream(self):
        """Test error handling when left stream is missing."""
        component = ETLDualStreamJoinComponent(
            left_stream=None,
            right_stream=[Data(data={"id": 1})],
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        with pytest.raises(ValueError):
            component.join_streams()

    def test_invalid_field_name(self):
        """Test error handling with invalid field names."""
        left_data = [Data(data={"id": 1})]
        right_data = [Data(data={"id": 1})]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "nonexistent_field", "operator": "=", "right_key": "id"}],
        )

        with pytest.raises(ValueError):
            component.join_streams()

    # ==================== 测试组9: 字段提取功能 ====================

    def test_extract_field_names(self):
        """Test field name extraction from data stream."""
        data = [
            Data(data={"field1": "value1", "field2": "value2", "field3": "value3"}),
        ]

        component = ETLDualStreamJoinComponent()
        fields = component._extract_field_names(data)

        assert len(fields) == 3
        assert "field1" in fields
        assert "field2" in fields
        assert "field3" in fields

    def test_extract_field_names_empty_stream(self):
        """Test field extraction from empty stream."""
        component = ETLDualStreamJoinComponent()
        fields = component._extract_field_names([])

        assert fields == []

    def test_extract_field_names_dict_data(self):
        """Test field extraction from plain dict data."""
        data = [{"key1": "val1", "key2": "val2"}]

        component = ETLDualStreamJoinComponent()
        fields = component._extract_field_names(data)

        assert len(fields) == 2
        assert "key1" in fields
        assert "key2" in fields

    # ==================== 测试组10: update_build_config ====================

    def test_update_build_config_load_fields(self):
        """Test dynamic field loading via update_build_config."""
        left_data = [Data(data={"id": 1, "name": "Alice"})]
        right_data = [Data(data={"id": 1, "email": "alice@example.com"})]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
        )

        build_config = {
            "join_conditions": {
                "table_schema": [
                    {"name": "left_key", "options": []},
                    {"name": "operator", "options": []},
                    {"name": "right_key", "options": []},
                ]
            }
        }

        updated_config = component.update_build_config(
            build_config, field_value=None, field_name="join_conditions", action="load_fields"
        )

        # Check left fields are loaded
        assert "id" in updated_config["join_conditions"]["table_schema"][0]["options"]
        assert "name" in updated_config["join_conditions"]["table_schema"][0]["options"]

        # Check right fields are loaded
        assert "id" in updated_config["join_conditions"]["table_schema"][2]["options"]
        assert "email" in updated_config["join_conditions"]["table_schema"][2]["options"]

    # ==================== 测试组11: 统计信息 ====================

    def test_get_join_stats(self):
        """Test join statistics output."""
        left_data = [Data(data={"id": i}) for i in range(10)]
        right_data = [Data(data={"id": i}) for i in range(5)]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        stats = component.get_join_stats()

        assert stats.data["join_type"] == "inner"
        assert stats.data["left_stream_count"] == 10
        assert stats.data["right_stream_count"] == 5
        assert stats.data["joined_count"] == 5

    # ==================== 测试组12: 字段预览 ====================

    def test_preview_fields(self):
        """Test field preview functionality."""
        left_data = [Data(data={"id": 1, "name": "Alice", "shared": "left_value"})]
        right_data = [Data(data={"id": 1, "email": "alice@example.com", "shared": "right_value"})]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            left_prefix="L",
            right_prefix="R",
        )

        preview = component.preview_fields()

        assert preview.data["left_fields_count"] == 3
        assert preview.data["right_fields_count"] == 3
        assert preview.data["common_fields_count"] == 2  # id and shared
        assert preview.data["total_fields"] > 0

    # ==================== 测试组13: 数据类型兼容性 ====================

    def test_mixed_data_types(self):
        """Test join with mixed data types."""
        left_data = [
            Data(data={"id": 1, "value": 100, "flag": True, "name": "Test"}),
        ]

        right_data = [
            Data(data={"id": 1, "score": 95.5, "count": 10}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        result = component.join_streams()

        assert len(result) == 1
        assert isinstance(result[0].data["value"], int)
        assert isinstance(result[0].data["flag"], bool)
        assert isinstance(result[0].data["score"], float)

    def test_null_values_in_join_keys(self):
        """Test behavior with null values in join keys."""
        left_data = [
            Data(data={"id": 1, "name": "Alice"}),
            Data(data={"id": None, "name": "Bob"}),
        ]

        right_data = [
            Data(data={"id": 1, "email": "alice@example.com"}),
            Data(data={"id": None, "email": "unknown@example.com"}),
        ]

        component = ETLDualStreamJoinComponent(
            left_stream=left_data,
            right_stream=right_data,
            join_type="inner",
            join_conditions=[{"left_key": "id", "operator": "=", "right_key": "id"}],
        )

        result = component.join_streams()

        # Pandas typically doesn't match NaN/None in joins
        # Should only match id=1
        assert len(result) >= 1


# ==================== 集成测试 ====================


class TestETLDualStreamJoinIntegration:
    """Integration tests simulating real-world scenarios."""

    def test_order_bill_expense_scenario(self):
        """Test the example from user manual: joining orders, bills, and expenses."""
        # Simulating the scenario from the manual
        order_data = [
            Data(data={"订单号": "ORD001", "商品": "iPhone", "数量": 1}),
            Data(data={"订单号": "ORD002", "商品": "MacBook", "数量": 1}),
        ]

        bill_data = [
            Data(data={"订单编号": "ORD001", "商户订单号": "BILL001", "金额": 999}),
            Data(data={"订单编号": "ORD002", "商户订单号": "BILL002", "金额": 1999}),
        ]

        # First join: orders + bills
        join1 = ETLDualStreamJoinComponent(
            left_stream=order_data,
            right_stream=bill_data,
            join_type="inner",
            join_conditions=[{"left_key": "订单号", "operator": "=", "right_key": "订单编号"}],
        )

        result1 = join1.join_streams()
        assert len(result1) == 2

        # Second join: result1 + expenses (simulated)
        expense_data = [
            Data(data={"商户订单号": "BILL001", "费用": 50}),
            Data(data={"商户订单号": "BILL002", "费用": 100}),
        ]

        join2 = ETLDualStreamJoinComponent(
            left_stream=result1,
            right_stream=expense_data,
            join_type="left",
            join_conditions=[{"left_key": "商户订单号", "operator": "=", "right_key": "商户订单号"}],
        )

        final_result = join2.join_streams()
        assert len(final_result) == 2
