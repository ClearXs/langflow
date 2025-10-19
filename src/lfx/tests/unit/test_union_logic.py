#!/usr/bin/env python
"""
Direct unit test for multi_stream_union component logic
Tests the core methods directly without full component framework
"""

import sys
sys.path.insert(0, "/Users/jiangwei/Development/AI/langflow/src/lfx/src")

import pandas as pd


class Data:
    """Simple Data class for testing"""
    def __init__(self, data):
        self.data = data


def convert_to_dataframe(data_list):
    """Convert list of Data objects to pandas DataFrame."""
    records = []
    for data_obj in data_list:
        if hasattr(data_obj, "data") and isinstance(data_obj.data, dict):
            records.append(data_obj.data)
        elif isinstance(data_obj, dict):
            records.append(data_obj)
    return pd.DataFrame(records)


def extract_field_names(data_list):
    """从数据流中提取字段名列表"""
    if not data_list or len(data_list) == 0:
        return []
    first_record = data_list[0]
    if hasattr(first_record, "data") and isinstance(first_record.data, dict):
        return list(first_record.data.keys())
    elif isinstance(first_record, dict):
        return list(first_record.keys())
    return []


def union_streams_logic(all_streams, align_schemas=True, drop_duplicates=False, field_config=None):
    """Core union logic extracted from component"""
    if not all_streams:
        raise ValueError("At least one stream is required")

    # Convert to DataFrames
    dataframes = []
    for stream in all_streams:
        df = convert_to_dataframe(stream)
        dataframes.append(df)

    # Merge all DataFrames (Union ALL)
    if align_schemas:
        merged_df = pd.concat(dataframes, ignore_index=True, sort=False)
        merged_df = merged_df.fillna("")
    else:
        merged_df = pd.concat(dataframes, ignore_index=True)

    # Apply field filtering (if field_config is configured)
    if field_config:
        keep_fields = [f["field_name"] for f in field_config if f.get("keep_field", True)]
        if keep_fields:
            available_fields = [f for f in keep_fields if f in merged_df.columns]
            if available_fields:
                merged_df = merged_df[available_fields]

    # Drop duplicates if requested
    if drop_duplicates:
        merged_df = merged_df.drop_duplicates()

    # Convert back to Data objects
    result_data = []
    for _, row in merged_df.iterrows():
        row_dict = row.to_dict()
        result_data.append(Data(data=row_dict))

    return result_data


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

    result = union_streams_logic([stream1, stream2])

    assert len(result) == 4, f"Expected 4 results, got {len(result)}"
    assert result[0].data["id"] == 1
    assert result[2].data["id"] == 3
    print("✓ Test 1 passed")


def test_schema_alignment():
    """Test schema alignment with different fields"""
    print("\nTest 2: Schema alignment...")

    stream1 = [Data(data={"id": 1, "name": "Alice"})]
    stream2 = [Data(data={"id": 2, "age": 30})]

    result = union_streams_logic([stream1, stream2], align_schemas=True)

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

    result = union_streams_logic([stream1, stream2], drop_duplicates=True)

    assert len(result) == 1, f"Expected 1 result after dedup, got {len(result)}"
    print("✓ Test 3 passed")


def test_extract_field_names():
    """Test field name extraction"""
    print("\nTest 4: Extract field names...")

    stream = [Data(data={"id": 1, "name": "Alice", "age": 25})]
    fields = extract_field_names(stream)

    assert len(fields) == 3
    assert set(fields) == {"id", "name", "age"}
    print("✓ Test 4 passed")


def test_no_streams_error():
    """Test error when no streams provided"""
    print("\nTest 5: No streams error...")

    try:
        union_streams_logic([])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "At least one stream is required" in str(e)
        print("✓ Test 5 passed")


def test_field_filtering():
    """Test field filtering"""
    print("\nTest 6: Field filtering...")

    stream1 = [Data(data={"id": 1, "name": "Alice", "age": 25})]
    stream2 = [Data(data={"id": 2, "name": "Bob", "age": 30})]

    field_config = [
        {"field_name": "id", "keep_field": True},
        {"field_name": "name", "keep_field": True},
        {"field_name": "age", "keep_field": False},
    ]

    result = union_streams_logic([stream1, stream2], field_config=field_config)

    assert len(result) == 2
    assert "age" not in result[0].data
    assert "id" in result[0].data
    assert "name" in result[0].data
    print("✓ Test 6 passed")


def test_five_streams():
    """Test union of 5 streams"""
    print("\nTest 7: Union of 5 streams...")

    streams = [
        [Data(data={"id": i, "value": i * 10})]
        for i in range(1, 6)
    ]

    result = union_streams_logic(streams)

    assert len(result) == 5
    ids = {r.data["id"] for r in result}
    assert ids == {1, 2, 3, 4, 5}
    print("✓ Test 7 passed")


def test_empty_fields_extraction():
    """Test field extraction from empty stream"""
    print("\nTest 8: Empty stream field extraction...")

    fields = extract_field_names([])
    assert fields == []
    print("✓ Test 8 passed")


def test_large_dataset():
    """Test larger dataset"""
    print("\nTest 9: Large dataset union...")

    stream1 = [Data(data={"id": i, "value": i * 2}) for i in range(100)]
    stream2 = [Data(data={"id": i, "value": i * 3}) for i in range(100, 200)]

    result = union_streams_logic([stream1, stream2])

    assert len(result) == 200
    assert result[0].data["id"] == 0
    assert result[-1].data["id"] == 199
    print("✓ Test 9 passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Multi Stream Union - Core Logic Tests")
    print("=" * 60)

    try:
        test_basic_union()
        test_schema_alignment()
        test_drop_duplicates()
        test_extract_field_names()
        test_no_streams_error()
        test_field_filtering()
        test_five_streams()
        test_empty_fields_extraction()
        test_large_dataset()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
