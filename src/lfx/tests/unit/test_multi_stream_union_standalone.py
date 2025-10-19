#!/usr/bin/env python
"""
Standalone test script for multi_stream_union component
Run with: python test_multi_stream_union_standalone.py
"""

import sys
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["i18n"] = MagicMock()
sys.modules["i18n"].t = lambda key, **kwargs: key.format(**kwargs) if kwargs else key

sys.modules["lfx"] = MagicMock()
sys.modules["lfx.custom"] = MagicMock()
sys.modules["lfx.custom.custom_component"] = MagicMock()
sys.modules["lfx.custom.custom_component.component"] = MagicMock()
sys.modules["lfx.io"] = MagicMock()
sys.modules["lfx.log"] = MagicMock()
sys.modules["lfx.log.logger"] = MagicMock()
sys.modules["lfx.schema"] = MagicMock()

# Now add actual path and import
sys.path.insert(0, "/Users/jiangwei/Development/AI/langflow/src/lfx/src")

import pandas as pd

# Minimal Data class for testing
class Data:
    def __init__(self, data):
        self.data = data


# Mock Component base class
class Component:
    status = ""


# Import only the methods we need to test
exec(open("/Users/jiangwei/Development/AI/langflow/src/lfx/src/lfx/components/operations/multi_stream_union.py").read())


def test_basic_union():
    """Test basic union of two streams"""
    print("Test 1: Basic union of two streams...")

    stream1 = [
        Data(data={"id": 1, "name": "Alice"}),
        Data(data={"id": 2, "name": "Bob"}),
    ]
    stream2 = [
        Data(data={"id": 3, "name": "Charlie"}),
        Data(data={"id": 4, "name": "David"}),
    ]

    component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2)

    # Debug: check if streams are set
    print(f"  Debug: stream_1 = {getattr(component, 'stream_1', 'NOT SET')}")
    print(f"  Debug: stream_2 = {getattr(component, 'stream_2', 'NOT SET')}")

    # Manually set if not working through constructor
    if not hasattr(component, 'stream_1') or component.stream_1 is None:
        component.stream_1 = stream1
    if not hasattr(component, 'stream_2') or component.stream_2 is None:
        component.stream_2 = stream2

    result = component.union_streams()

    assert len(result) == 4, f"Expected 4 results, got {len(result)}"
    assert result[0].data["id"] == 1
    assert result[2].data["id"] == 3
    print("✓ Test 1 passed")


def test_schema_alignment():
    """Test schema alignment with different fields"""
    print("\nTest 2: Schema alignment...")

    stream1 = [Data(data={"id": 1, "name": "Alice"})]
    stream2 = [Data(data={"id": 2, "age": 30})]

    component = ETLMultiStreamUnionComponent()
    component.stream_1 = stream1
    component.stream_2 = stream2
    component.align_schemas = True

    result = component.union_streams()

    assert len(result) == 2
    assert "name" in result[0].data
    assert "age" in result[0].data
    assert result[0].data["age"] == ""  # Filled with empty string
    assert result[1].data["name"] == ""  # Filled with empty string
    print("✓ Test 2 passed")


def test_drop_duplicates():
    """Test duplicate removal"""
    print("\nTest 3: Drop duplicates...")

    stream1 = [Data(data={"id": 1, "name": "Alice"})]
    stream2 = [Data(data={"id": 1, "name": "Alice"})]

    component = ETLMultiStreamUnionComponent()
    component.stream_1 = stream1
    component.stream_2 = stream2
    component.drop_duplicates = True

    result = component.union_streams()

    assert len(result) == 1, f"Expected 1 result after dedup, got {len(result)}"
    print("✓ Test 3 passed")


def test_field_preview():
    """Test field preview functionality"""
    print("\nTest 4: Field preview...")

    stream1 = [Data(data={"id": 1, "name": "Alice"})]
    stream2 = [Data(data={"id": 2, "name": "Bob", "age": 30})]

    component = ETLMultiStreamUnionComponent()
    component.stream_1 = stream1
    component.stream_2 = stream2

    preview = component.preview_fields()

    assert preview.data["total_fields"] == 3
    assert preview.data["total_streams"] == 2
    print("✓ Test 4 passed")


def test_extract_field_names():
    """Test field name extraction"""
    print("\nTest 5: Extract field names...")

    stream = [Data(data={"id": 1, "name": "Alice", "age": 25})]

    component = ETLMultiStreamUnionComponent()
    component.stream_1 = stream

    fields = component._extract_field_names(stream)

    assert len(fields) == 3
    assert set(fields) == {"id", "name", "age"}
    print("✓ Test 5 passed")


def test_no_streams_error():
    """Test error when no streams provided"""
    print("\nTest 6: No streams error...")

    component = ETLMultiStreamUnionComponent()

    try:
        component.union_streams()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "no_streams" in str(e) or "至少需要一个数据流" in str(e)
        print("✓ Test 6 passed")


def test_field_filtering():
    """Test field filtering"""
    print("\nTest 7: Field filtering...")

    stream1 = [Data(data={"id": 1, "name": "Alice", "age": 25})]
    stream2 = [Data(data={"id": 2, "name": "Bob", "age": 30})]

    field_config = [
        {"field_name": "id", "keep_field": True},
        {"field_name": "name", "keep_field": True},
        {"field_name": "age", "keep_field": False},
    ]

    component = ETLMultiStreamUnionComponent()
    component.stream_1 = stream1
    component.stream_2 = stream2
    component.field_config = field_config

    result = component.union_streams()

    assert len(result) == 2
    assert "age" not in result[0].data
    assert "id" in result[0].data
    assert "name" in result[0].data
    print("✓ Test 7 passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Multi Stream Union Component Tests")
    print("=" * 60)

    try:
        test_basic_union()
        test_schema_alignment()
        test_drop_duplicates()
        test_field_preview()
        test_extract_field_names()
        test_no_streams_error()
        test_field_filtering()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
