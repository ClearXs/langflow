"""GDB data models (Pydantic)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GDBLayerInfo(BaseModel):
    """GDB 图层信息模型."""

    name: str = Field(description="图层名称")
    feature_count: int = Field(description="要素数量")
    geometry_type: str = Field(description="几何类型")
    spatial_ref: str | None = Field(default=None, description="空间参考（WKT 格式）")
    extent: dict[str, float] | None = Field(default=None, description="空间范围 (minX, minY, maxX, maxY)")


class GDBFieldInfo(BaseModel):
    """GDB 字段信息模型."""

    name: str = Field(description="字段名称")
    alias: str | None = Field(default=None, description="字段别名（备注）")
    type: str = Field(description="字段类型")
    width: int = Field(description="字段宽度")


class GDBFeature(BaseModel):
    """GDB 要素模型."""

    id: int = Field(description="要素 ID")
    geometry: str | None = Field(default=None, description="几何对象（WKT 格式）")
    properties: dict[str, Any] = Field(default_factory=dict, description="属性字段")


class GDBLayerData(BaseModel):
    """GDB 图层数据模型."""

    layer_name: str = Field(description="图层名称")
    fields: list[GDBFieldInfo] = Field(description="字段列表")
    features: list[GDBFeature] = Field(description="要素列表")
    total_count: int = Field(description="总要素数量")
    warning: str | None = Field(default=None, description="警告信息（如：特殊图层类型、无法读取字段等）")


class GDBExtractResult(BaseModel):
    """GDB 解压结果模型."""

    gdb_path: str = Field(description="解压后的 GDB 路径")
    gdb_name: str = Field(description="GDB 名称")
    layer_count: int = Field(description="图层数量")


class GDBNodeType(str, Enum):
    """GDB 节点类型枚举."""

    ROOT = "root"
    FEATURE_DATASET = "dataset"
    FEATURE_CLASS = "featureclass"
    TABLE = "table"


class GDBTreeNode(BaseModel):
    """GDB 树形节点模型（递归）."""

    name: str = Field(description="节点名称")
    node_type: GDBNodeType = Field(description="节点类型")
    path: str = Field(description="层次路径，如 /Transportation/Roads")
    feature_count: int | None = Field(default=None, description="要素数量（仅图层）")
    geometry_type: str | None = Field(default=None, description="几何类型（仅要素类）")
    spatial_ref: str | None = Field(default=None, description="空间参考（WKT 格式）")
    extent: dict[str, float] | None = Field(default=None, description="空间范围")
    data: "GDBLayerData | None" = Field(default=None, description="图层数据（可选）")
    children: list["GDBTreeNode"] = Field(default_factory=list, description="子节点")


class GDBTreeStructure(BaseModel):
    """GDB 完整树形结构模型."""

    gdb_name: str = Field(description="GDB 名称")
    gdb_path: str = Field(description="GDB 路径")
    total_layers: int = Field(description="总图层数量")
    total_datasets: int = Field(description="总 FeatureDataset 数量")
    root: GDBTreeNode = Field(description="根节点")


# 支持前向引用
GDBTreeNode.model_rebuild()

