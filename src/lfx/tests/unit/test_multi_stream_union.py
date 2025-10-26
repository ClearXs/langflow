"""Unit tests for ETLMultiStreamUnionComponent"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock i18n module
sys.modules["i18n"] = MagicMock()

from lfx.components.operations.multi_stream_union import ETLMultiStreamUnionComponent
from lfx.schema import Data


# Setup i18n mock to return key as value
def mock_i18n_t(key, **kwargs):
    """Mock i18n.t function to return formatted string"""
    if kwargs:
        return key.format(**kwargs)
    return key


sys.modules["i18n"].t = mock_i18n_t


class TestETLMultiStreamUnionComponent:
    """Test suite for Multi Stream Union component"""

    def test_basic_union_two_streams(self):
        """测试2个流的基本合并"""
        # 准备测试数据
        stream1 = [
            Data(data={"id": 1, "name": "Alice"}),
            Data(data={"id": 2, "name": "Bob"}),
        ]
        stream2 = [
            Data(data={"id": 3, "name": "Charlie"}),
            Data(data={"id": 4, "name": "David"}),
        ]

        # 执行合并
        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2)
        result = component.union_streams()

        # 验证
        assert len(result) == 4
        assert result[0].data["id"] == 1
        assert result[2].data["id"] == 3

    def test_basic_union_five_streams(self):
        """测试5个流的合并"""
        streams_data = {}
        for i in range(1, 6):
            streams_data[f"stream_{i}"] = [Data(data={"id": i, "value": i * 10})]

        component = ETLMultiStreamUnionComponent(**streams_data)
        result = component.union_streams()

        assert len(result) == 5
        # 验证每个流的数据都在结果中
        ids = [r.data["id"] for r in result]
        assert set(ids) == {1, 2, 3, 4, 5}

    def test_schema_alignment(self):
        """测试不同schema的流合并时的对齐"""
        stream1 = [Data(data={"id": 1, "name": "Alice"})]
        stream2 = [Data(data={"id": 2, "age": 30})]  # 不同字段

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2, align_schemas=True)
        result = component.union_streams()

        # 验证所有记录都有id, name, age字段（缺失的填充空值）
        assert len(result) == 2
        assert "name" in result[0].data
        assert "age" in result[0].data  # 来自stream1，age应该被填充为空
        assert "name" in result[1].data  # 来自stream2，name应该被填充为空
        assert "age" in result[1].data

        # 验证缺失字段被填充为空字符串
        assert result[0].data["age"] == ""
        assert result[1].data["name"] == ""

    def test_drop_duplicates(self):
        """测试去重功能"""
        stream1 = [Data(data={"id": 1, "name": "Alice"})]
        stream2 = [Data(data={"id": 1, "name": "Alice"})]  # 重复数据

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2, drop_duplicates=True)
        result = component.union_streams()

        assert len(result) == 1  # 去重后只有1条

    def test_drop_duplicates_disabled(self):
        """测试不去重时保留重复数据"""
        stream1 = [Data(data={"id": 1, "name": "Alice"})]
        stream2 = [Data(data={"id": 1, "name": "Alice"})]  # 重复数据

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2, drop_duplicates=False)
        result = component.union_streams()

        assert len(result) == 2  # 不去重，保留2条

    def test_include_source_info(self):
        """测试添加来源信息"""
        stream1 = [Data(data={"id": 1, "name": "Alice"})]
        stream2 = [Data(data={"id": 2, "name": "Bob"})]

        component = ETLMultiStreamUnionComponent(
            stream_1=stream1, stream_2=stream2, include_source_info=True, source_column="_source"
        )
        result = component.union_streams()

        assert len(result) == 2
        assert result[0].data["_source"] == "stream_1"
        assert result[1].data["_source"] == "stream_2"

    def test_field_preview(self):
        """测试字段预览功能"""
        stream1 = [Data(data={"id": 1, "name": "Alice"})]
        stream2 = [Data(data={"id": 2, "name": "Bob", "age": 30})]

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2)
        preview = component.preview_fields()

        assert preview.data["total_fields"] == 3  # id, name, age
        assert preview.data["total_streams"] == 2

        # 验证字段信息
        fields = {f["field_name"]: f for f in preview.data["fields"]}
        assert "id" in fields
        assert "name" in fields
        assert "age" in fields

        # id和name出现在2个流中
        assert fields["id"]["appears_in_streams"] == 2
        assert fields["name"]["appears_in_streams"] == 2
        # age只出现在stream_2中
        assert fields["age"]["appears_in_streams"] == 1
        assert "stream_2" in fields["age"]["sources"]

    def test_extract_field_names(self):
        """测试字段名提取"""
        stream = [Data(data={"id": 1, "name": "Alice", "age": 25})]

        component = ETLMultiStreamUnionComponent(stream_1=stream)
        fields = component._extract_field_names(stream)

        assert len(fields) == 3
        assert set(fields) == {"id", "name", "age"}

    def test_extract_field_names_empty_stream(self):
        """测试空流的字段提取"""
        component = ETLMultiStreamUnionComponent()
        fields = component._extract_field_names([])

        assert fields == []

    def test_update_build_config_load_fields(self):
        """测试字段加载功能"""
        stream1 = [Data(data={"id": 1, "name": "Alice", "age": 25})]
        stream2 = [Data(data={"id": 2, "name": "Bob", "city": "NYC"})]

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2)

        # 测试字段加载
        build_config = {"field_config": {"value": []}}
        build_config = component.update_build_config(build_config, None, "field_config", "load_fields")

        # 验证加载的字段
        field_config = build_config["field_config"]["value"]
        assert len(field_config) == 4  # id, name, age, city

        # 验证字段信息
        field_names = {f["field_name"] for f in field_config}
        assert field_names == {"id", "name", "age", "city"}

        # 验证所有字段默认保留
        for field in field_config:
            assert field["keep_field"] is True

        # 验证来源信息
        fields_dict = {f["field_name"]: f for f in field_config}
        assert "stream_1, stream_2" in fields_dict["id"]["source_stream"]
        assert "stream_1" in fields_dict["age"]["source_stream"]
        assert "stream_2" in fields_dict["city"]["source_stream"]

    def test_field_filtering(self):
        """测试字段过滤功能"""
        stream1 = [Data(data={"id": 1, "name": "Alice", "age": 25})]
        stream2 = [Data(data={"id": 2, "name": "Bob", "age": 30})]

        # 设置只保留id和name
        field_config = [
            {"field_name": "id", "source_stream": "stream_1, stream_2", "keep_field": True},
            {"field_name": "name", "source_stream": "stream_1, stream_2", "keep_field": True},
            {"field_name": "age", "source_stream": "stream_1, stream_2", "keep_field": False},
        ]

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2, field_config=field_config)

        result = component.union_streams()

        assert len(result) == 2
        # 验证age字段被过滤
        assert "age" not in result[0].data
        assert "age" not in result[1].data
        # 验证id和name字段保留
        assert "id" in result[0].data
        assert "name" in result[0].data

    def test_no_streams_error(self):
        """测试没有数据流时的错误处理"""
        component = ETLMultiStreamUnionComponent()

        with pytest.raises(ValueError, match="至少需要一个数据流|At least one stream is required"):
            component.union_streams()

    def test_get_union_stats(self):
        """测试统计信息"""
        stream1 = [Data(data={"id": 1}), Data(data={"id": 2})]
        stream2 = [Data(data={"id": 3}), Data(data={"id": 4}), Data(data={"id": 5})]

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2, drop_duplicates=True)
        stats = component.get_union_stats()

        assert stats.data["total_streams"] == 2
        assert stats.data["stream_counts"] == [2, 3]
        assert stats.data["merged_count"] == 5
        assert stats.data["drop_duplicates"] is True
        assert stats.data["align_schemas"] is True

    def test_convert_to_dataframe(self):
        """测试Data对象转DataFrame"""
        data_list = [Data(data={"id": 1, "name": "Alice"}), Data(data={"id": 2, "name": "Bob"})]

        component = ETLMultiStreamUnionComponent()
        df = component._convert_to_dataframe(data_list)

        assert len(df) == 2
        assert list(df.columns) == ["id", "name"]
        assert df.iloc[0]["id"] == 1
        assert df.iloc[1]["name"] == "Bob"

    def test_union_with_single_stream(self):
        """测试单个流的合并（边界情况）"""
        stream1 = [Data(data={"id": 1, "name": "Alice"}), Data(data={"id": 2, "name": "Bob"})]

        component = ETLMultiStreamUnionComponent(stream_1=stream1)
        result = component.union_streams()

        assert len(result) == 2
        assert result[0].data["id"] == 1
        assert result[1].data["id"] == 2

    def test_union_with_empty_dataframe_fields(self):
        """测试空DataFrame的处理"""
        stream1 = []  # 空流

        component = ETLMultiStreamUnionComponent(stream_1=stream1)

        # 空流应该被忽略，因为getattr会返回空列表但长度为0
        # 这会导致没有流的错误
        with pytest.raises(ValueError, match="至少需要一个数据流|At least one stream is required"):
            component.union_streams()

    def test_field_preview_no_streams(self):
        """测试无流时的字段预览"""
        component = ETLMultiStreamUnionComponent()
        preview = component.preview_fields()

        assert preview.data["fields"] == []
        assert "message" in preview.data

    def test_large_dataset_union(self):
        """测试大数据集合并（性能测试）"""
        # 创建较大的数据集
        stream1 = [Data(data={"id": i, "value": i * 2}) for i in range(1000)]
        stream2 = [Data(data={"id": i, "value": i * 3}) for i in range(1000, 2000)]

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2)
        result = component.union_streams()

        assert len(result) == 2000
        # 验证第一条和最后一条
        assert result[0].data["id"] == 0
        assert result[-1].data["id"] == 1999

    def test_union_with_none_values(self):
        """测试包含None值的数据合并"""
        stream1 = [Data(data={"id": 1, "name": "Alice", "age": None})]
        stream2 = [Data(data={"id": 2, "name": None, "age": 30})]

        component = ETLMultiStreamUnionComponent(stream_1=stream1, stream_2=stream2, align_schemas=True)
        result = component.union_streams()

        assert len(result) == 2
        # None值应该被填充为空字符串
        assert result[0].data["age"] == ""
        assert result[1].data["name"] == ""
