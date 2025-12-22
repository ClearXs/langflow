# GDB文件读取API - 后端实施指南

> 更新时间: 2025-12-16
> 版本: v2.0
>
> **重要**: 本文档基于 Langflow 三层架构设计，核心业务逻辑放在 LFX 层，Backend 层只定义 API 接口。

## 目录

- [1. 功能概述](#1-功能概述)
- [2. 技术架构](#2-技术架构)
- [3. GDAL使用方式](#3-gdal使用方式基于aqmi项目分析)
- [4. 实施步骤](#4-实施步骤)
- [5. 使用示例](#5-使用示例)
- [6. 测试验证](#6-测试验证)
- [7. 注意事项](#7-注意事项)
- [8. 后续扩展](#8-后续扩展)

---

## 1. 功能概述

本功能用于在 Langflow 后端暴露 API 接口，支持读取和解析 `.gdb.zip` 格式的 ESRI File Geodatabase 文件。

**核心功能**:
- 上传 `.gdb.zip` 文件
- 解压缩并读取 GDB 数据
- 列出 GDB 中的所有图层（Layer）
- 读取指定图层的字段信息和要素数据
- 支持空间参考系统（SRS）信息

**技术栈**:
- **GDAL/OGR**: 地理数据读取库（核心依赖）
- **FastAPI**: Web 框架（Backend 层）
- **Pydantic**: 数据模型（LFX 层）
- **SQLModel**: 数据库 ORM（Backend 层）
- **Python zipfile**: ZIP 文件处理

---

## 2. 技术架构

**重要**: 遵循 Langflow 的三层架构，核心业务逻辑放在 LFX，Backend 只定义 API 接口。

```
┌─────────────────────────────────────────────────────────────┐
│                   Backend 层 (API 接口定义)                  │
│  src/backend/base/langflow/api/v1/gdb.py                   │
│  - POST /api/v1/gdb/upload         上传 GDB ZIP 文件       │
│  - GET  /api/v1/gdb/{id}/layers    获取图层列表            │
│  - GET  /api/v1/gdb/{id}/layer/{name}  获取图层数据        │
│  - DELETE /api/v1/gdb/{id}         删除 GDB 文件           │
│                                                             │
│  src/backend/base/langflow/services/database/models/gdb/    │
│  - model.py                    数据库模型（SQLModel）       │
└─────────────────────────────────────────────────────────────┘
                              ↓ 调用
┌─────────────────────────────────────────────────────────────┐
│                   LFX 层 (核心业务逻辑)                      │
│  src/lfx/src/lfx/services/gdb/service.py                   │
│  - GDBService                  核心服务类                   │
│    - extract_gdb_from_zip()    解压 ZIP 文件               │
│    - read_gdb_layers()         读取图层列表                │
│    - read_layer_data()         读取图层数据                │
│    - delete_gdb_storage()      删除存储文件                │
│                                                             │
│  src/lfx/src/lfx/services/gdb/models.py                    │
│  - GDBLayerInfo                图层信息模型（Pydantic）     │
│  - GDBLayerData                图层数据模型（Pydantic）     │
│  - GDBFeature                  要素模型（Pydantic）         │
│  - GDBFieldInfo                字段信息模型（Pydantic）     │
│  - GDBExtractResult            解压结果模型（Pydantic）     │
└─────────────────────────────────────────────────────────────┘
                              ↓ 使用
┌─────────────────────────────────────────────────────────────┐
│                   GDAL/OGR 库                               │
│  from osgeo import gdal, ogr, osr                           │
└─────────────────────────────────────────────────────────────┘
```

**架构原则**:
- **LFX 层**: 包含所有 GDAL 操作、文件处理、业务逻辑，不依赖 FastAPI
- **Backend 层**: 只处理 HTTP 请求、数据库操作、用户认证，调用 LFX 提供的服务

---

## 3. GDAL使用方式（基于AQMI项目分析）

### 3.1 核心导入

```python
from osgeo import gdal, ogr, osr
import os

# 启用 GDAL 异常
gdal.UseExceptions()
```

### 3.2 打开 GDB 数据源

```python
# 打开 OpenFileGDB 驱动（只读模式）
driver = ogr.GetDriverByName("OpenFileGDB")
data_source = driver.Open("/path/to/extracted.gdb", 0)  # 0 = 只读

if data_source is None:
    raise Exception("无法打开 GDB 文件")
```

### 3.3 列出所有图层

```python
layer_count = data_source.GetLayerCount()
layers = []

for i in range(layer_count):
    layer = data_source.GetLayerByIndex(i)
    layer_info = {
        "name": layer.GetName(),
        "feature_count": layer.GetFeatureCount(),
        "geometry_type": ogr.GeometryTypeToName(layer.GetGeomType()),
        "spatial_ref": layer.GetSpatialRef().ExportToWkt() if layer.GetSpatialRef() else None
    }
    layers.append(layer_info)
```

### 3.4 读取图层字段架构

```python
layer = data_source.GetLayerByName("layer_name")
layer_defn = layer.GetLayerDefn()

fields = []
for i in range(layer_defn.GetFieldCount()):
    field_defn = layer_defn.GetFieldDefn(i)
    fields.append({
        "name": field_defn.GetName(),
        "type": field_defn.GetFieldTypeName(field_defn.GetType()),
        "width": field_defn.GetWidth()
    })
```

### 3.5 读取要素数据

```python
features = []
layer.ResetReading()  # 重置读取指针

for feature in layer:
    feature_data = {
        "id": feature.GetFID(),
        "geometry": feature.GetGeometryRef().ExportToWkt() if feature.GetGeometryRef() else None,
        "properties": {}
    }

    # 读取所有字段值
    for i in range(layer_defn.GetFieldCount()):
        field_name = layer_defn.GetFieldDefn(i).GetName()
        feature_data["properties"][field_name] = feature.GetField(i)

    features.append(feature_data)
```

### 3.6 资源清理

```python
# 释放资源（非常重要！）
data_source = None
layer = None
feature = None
```

---

## 4. 实施步骤

**实施顺序**: 先安装依赖，再实现 LFX 层（核心逻辑），最后实现 Backend 层（API 接口）

### 步骤 0: 安装 GDAL 依赖

#### 0.1 安装系统级 GDAL

**Windows (推荐使用 Conda)**:
```bash
# 方案 1: 使用 Conda（最简单）
conda install -c conda-forge gdal

# 方案 2: 使用 OSGeo4W
# 下载: https://trac.osgeo.org/osgeo4w/
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install -y gdal-bin libgdal-dev
```

**macOS**:
```bash
brew install gdal
```

#### 0.2 添加 GDAL 到 LFX 依赖

修改 `src/lfx/pyproject.toml`，在 `dependencies` 列表末尾添加：
```toml
dependencies = [
    # ... 其他依赖 ...
    "gdal>=3.6.0,<4.0.0",
]
```

#### 0.3 重新安装项目依赖

```bash
# 进入项目根目录
cd d:\corporation\imagtel\awesome-programmer\gfkd-ds\langflow

# 重新同步依赖
uv sync

# 或者单独安装 LFX
cd src/lfx
uv pip install -e .
```

#### 0.4 验证 GDAL 安装

```bash
uv run python -c "from osgeo import gdal, ogr; print(f'GDAL version: {gdal.__version__}')"
```

**期望输出**: `GDAL version: 3.x.x`

---

### 步骤 1: LFX 层 - 数据模型定义

**文件路径**: `src/lfx/src/lfx/services/gdb/models.py`

```python
"""GDB data models (Pydantic)."""

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


class GDBExtractResult(BaseModel):
    """GDB 解压结果模型."""

    gdb_path: str = Field(description="解压后的 GDB 路径")
    gdb_name: str = Field(description="GDB 名称")
    layer_count: int = Field(description="图层数量")
```

### 步骤 2: LFX 层 - 核心服务实现

**文件路径**: `src/lfx/src/lfx/services/gdb/service.py`

```python
"""GDB file service - Core business logic."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from osgeo import gdal, ogr

from lfx.services.gdb.models import (
    GDBExtractResult,
    GDBFeature,
    GDBFieldInfo,
    GDBLayerData,
    GDBLayerInfo,
)


class GDBService:
    """GDB 文件处理核心服务."""

    def __init__(self, storage_path: str | None = None):
        """
        初始化 GDB 服务.

        Args:
            storage_path: GDB 文件存储路径，默认使用系统临时目录
        """
        self.storage_path = storage_path or os.path.join(tempfile.gettempdir(), "langflow_gdb")
        os.makedirs(self.storage_path, exist_ok=True)

        # 启用 GDAL 异常
        gdal.UseExceptions()

    def extract_gdb_from_zip(self, zip_path: str, gdb_id: str) -> GDBExtractResult:
        """
        从 ZIP 文件中解压 GDB.

        Args:
            zip_path: ZIP 文件路径
            gdb_id: GDB 唯一标识符

        Returns:
            GDBExtractResult: 解压结果

        Raises:
            ValueError: ZIP 文件无效或不包含 .gdb 目录
            zipfile.BadZipFile: ZIP 文件损坏
        """
        extract_dir = os.path.join(self.storage_path, gdb_id)
        os.makedirs(extract_dir, exist_ok=True)

        try:
            # 解压 ZIP 文件
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 查找 .gdb 目录
            gdb_path = None
            gdb_name = None

            for root, dirs, _files in os.walk(extract_dir):
                for dir_name in dirs:
                    if dir_name.endswith(".gdb"):
                        gdb_path = os.path.join(root, dir_name)
                        gdb_name = dir_name.replace(".gdb", "")
                        break
                if gdb_path:
                    break

            if not gdb_path:
                # 清理失败的解压目录
                shutil.rmtree(extract_dir, ignore_errors=True)
                raise ValueError("ZIP 文件中未找到 .gdb 目录")

            # 验证 GDB 文件有效性并获取图层数量
            layer_count = self._get_layer_count(gdb_path)

            return GDBExtractResult(
                gdb_path=gdb_path,
                gdb_name=gdb_name,
                layer_count=layer_count,
            )

        except zipfile.BadZipFile as e:
            # 清理失败的解压目录
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise ValueError(f"无效的 ZIP 文件: {e}") from e

        except Exception as e:
            # 清理失败的解压目录
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise

    def read_gdb_layers(self, gdb_path: str) -> list[GDBLayerInfo]:
        """
        读取 GDB 文件中的所有图层信息.

        Args:
            gdb_path: GDB 目录路径

        Returns:
            list[GDBLayerInfo]: 图层信息列表

        Raises:
            ValueError: GDB 文件无效或无法打开
        """
        driver = ogr.GetDriverByName("OpenFileGDB")
        data_source = driver.Open(gdb_path, 0)  # 0 = 只读模式

        if data_source is None:
            raise ValueError(f"无法打开 GDB 文件: {gdb_path}")

        try:
            layers = []
            layer_count = data_source.GetLayerCount()

            for i in range(layer_count):
                layer = data_source.GetLayerByIndex(i)

                # 获取几何类型
                geom_type = layer.GetGeomType()
                geom_type_name = ogr.GeometryTypeToName(geom_type)

                # 获取空间参考
                srs = layer.GetSpatialRef()
                srs_wkt = srs.ExportToWkt() if srs else None

                # 获取空间范围
                extent = None
                try:
                    ext = layer.GetExtent()
                    if ext:
                        extent = {
                            "minX": ext[0],
                            "maxX": ext[1],
                            "minY": ext[2],
                            "maxY": ext[3],
                        }
                except Exception:
                    # 某些图层可能没有空间范围
                    pass

                layer_info = GDBLayerInfo(
                    name=layer.GetName(),
                    feature_count=layer.GetFeatureCount(),
                    geometry_type=geom_type_name,
                    spatial_ref=srs_wkt,
                    extent=extent,
                )
                layers.append(layer_info)

            return layers

        finally:
            # 释放资源
            data_source = None

    def read_layer_data(
        self,
        gdb_path: str,
        layer_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> GDBLayerData:
        """
        读取指定图层的数据.

        Args:
            gdb_path: GDB 目录路径
            layer_name: 图层名称
            limit: 返回要素数量限制
            offset: 偏移量

        Returns:
            GDBLayerData: 图层数据

        Raises:
            ValueError: GDB 文件无效或图层不存在
        """
        driver = ogr.GetDriverByName("OpenFileGDB")
        data_source = driver.Open(gdb_path, 0)

        if data_source is None:
            raise ValueError(f"无法打开 GDB 文件: {gdb_path}")

        try:
            layer = data_source.GetLayerByName(layer_name)
            if layer is None:
                raise ValueError(f"图层 '{layer_name}' 不存在")

            # 获取字段架构
            layer_defn = layer.GetLayerDefn()
            fields = []
            for i in range(layer_defn.GetFieldCount()):
                field_defn = layer_defn.GetFieldDefn(i)
                fields.append(
                    GDBFieldInfo(
                        name=field_defn.GetName(),
                        type=field_defn.GetFieldTypeName(field_defn.GetType()),
                        width=field_defn.GetWidth(),
                    )
                )

            # 读取要素数据
            features = []
            layer.ResetReading()

            # 跳过 offset 条记录
            for _ in range(offset):
                feature = layer.GetNextFeature()
                if feature is None:
                    break

            # 读取 limit 条记录
            count = 0
            while count < limit:
                feature = layer.GetNextFeature()
                if feature is None:
                    break

                # 读取几何
                geometry_wkt = None
                geom = feature.GetGeometryRef()
                if geom:
                    geometry_wkt = geom.ExportToWkt()

                # 读取属性
                properties = {}
                for i in range(layer_defn.GetFieldCount()):
                    field_name = layer_defn.GetFieldDefn(i).GetName()
                    properties[field_name] = feature.GetField(i)

                features.append(
                    GDBFeature(
                        id=feature.GetFID(),
                        geometry=geometry_wkt,
                        properties=properties,
                    )
                )
                count += 1

            total_count = layer.GetFeatureCount()

            return GDBLayerData(
                layer_name=layer_name,
                fields=fields,
                features=features,
                total_count=total_count,
            )

        finally:
            # 释放资源
            data_source = None

    def delete_gdb_storage(self, gdb_id: str) -> None:
        """
        删除 GDB 存储目录.

        Args:
            gdb_id: GDB 唯一标识符
        """
        gdb_dir = os.path.join(self.storage_path, gdb_id)
        if os.path.exists(gdb_dir):
            shutil.rmtree(gdb_dir, ignore_errors=True)

    def _get_layer_count(self, gdb_path: str) -> int:
        """获取 GDB 图层数量（内部方法）."""
        driver = ogr.GetDriverByName("OpenFileGDB")
        data_source = driver.Open(gdb_path, 0)

        if data_source is None:
            raise ValueError(f"无法打开 GDB 文件: {gdb_path}")

        try:
            return data_source.GetLayerCount()
        finally:
            data_source = None
```

### 步骤 3: LFX 层 - 模块导出

**文件路径**: `src/lfx/src/lfx/services/gdb/__init__.py`

```python
"""GDB service module."""

from lfx.services.gdb.models import (
    GDBExtractResult,
    GDBFeature,
    GDBFieldInfo,
    GDBLayerData,
    GDBLayerInfo,
)
from lfx.services.gdb.service import GDBService

__all__ = [
    "GDBService",
    "GDBLayerInfo",
    "GDBLayerData",
    "GDBFeature",
    "GDBFieldInfo",
    "GDBExtractResult",
]
```

### 步骤 4: Backend 层 - 数据库模型设计

**文件路径**: `src/backend/base/langflow/services/database/models/gdb/model.py`

```python
"""GDB File database models."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langflow.services.database.models.user import User


def get_utc_now():
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class GDBFileBase(SQLModel):
    """Base model for GDB file."""

    name: str = Field(index=True, description="GDB 文件名称")
    original_filename: str = Field(description="原始上传文件名")
    file_path: str = Field(description="解压后的 GDB 目录路径")
    file_size: int = Field(description="文件大小（字节）")
    layer_count: int = Field(default=0, description="图层数量")
    description: str | None = Field(default=None, description="文件描述")


class GDBFile(GDBFileBase, table=True):  # type: ignore[call-arg]
    """GDB file database model."""

    __tablename__ = "gdb_file"

    id: UUID = Field(default_factory=uuid4, primary_key=True, unique=True)
    created_at: datetime = Field(default_factory=get_utc_now, description="创建时间")
    updated_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column_kwargs={"onupdate": get_utc_now},
        description="更新时间",
    )
    user_id: UUID = Field(index=True, foreign_key="user.id")

    # Relationships
    user: "User" = Relationship(back_populates="gdb_files")


class GDBFileRead(GDBFileBase):
    """Schema for reading GDB file."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    user_id: UUID


class GDBFileCreate(GDBFileBase):
    """Schema for creating GDB file."""

    pass
```

**文件路径**: `src/backend/base/langflow/services/database/models/gdb/__init__.py`

```python
"""GDB database models module."""

from langflow.services.database.models.gdb.model import GDBFile, GDBFileCreate, GDBFileRead

__all__ = ["GDBFile", "GDBFileRead", "GDBFileCreate"]
```

**更新 User 模型** - 修改 `src/backend/base/langflow/services/database/models/user/model.py`:

```python
# 在文件顶部添加导入
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langflow.services.database.models.gdb import GDBFile

# 在 User 类中添加关系
class User(UserBase, table=True):
    # ... 其他字段 ...

    # Relationships
    gdb_files: list["GDBFile"] = Relationship(back_populates="user")
```

### 步骤 5: Backend 层 - API 接口实现

**文件路径**: `src/backend/base/langflow/api/v1/gdb.py`

**注意**: Backend 层只负责 HTTP 请求处理、数据库操作和用户认证，具体的 GDB 处理逻辑调用 LFX 层的 `GDBService`。

```python
"""GDB file API endpoints."""

import os
import tempfile
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import select

from langflow.api.utils import CurrentActiveUser
from langflow.services.database.models.gdb.model import GDBFile, GDBFileRead
from langflow.services.deps import get_session

# 从 LFX 层导入核心服务和模型
from lfx.services.gdb import GDBLayerData, GDBLayerInfo, GDBService

router = APIRouter(prefix="/gdb", tags=["GDB"])

# 创建全局 GDB 服务实例
gdb_service = GDBService()


@router.post("/upload", response_model=GDBFileRead, status_code=201)
async def upload_gdb_file(
    file: UploadFile = File(..., description="GDB ZIP 文件"),
    name: str | None = None,
    description: str | None = None,
    current_user: Annotated["User", Depends(CurrentActiveUser)] = None,
    session=Depends(get_session),
):
    """
    上传 GDB ZIP 文件。

    - **file**: .gdb.zip 格式的文件
    - **name**: GDB 文件名称（可选，默认使用文件名）
    - **description**: 文件描述（可选）
    """
    # 验证文件类型
    if not file.filename.endswith(".gdb.zip"):
        raise HTTPException(status_code=400, detail="只支持 .gdb.zip 格式的文件")

    # 保存上传文件到临时位置
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()

        file_size = len(content)
        gdb_id = str(uuid4())

        # 调用 LFX 层的服务解压文件
        try:
            extract_result = gdb_service.extract_gdb_from_zip(temp_file.name, gdb_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"解压文件失败: {e}") from e

        # 创建数据库记录
        gdb_file = GDBFile(
            id=UUID(gdb_id),
            name=name or extract_result.gdb_name,
            original_filename=file.filename,
            file_path=extract_result.gdb_path,
            file_size=file_size,
            layer_count=extract_result.layer_count,
            description=description,
            user_id=current_user.id,
        )

        session.add(gdb_file)
        session.commit()
        session.refresh(gdb_file)

        return gdb_file

    finally:
        # 清理临时文件
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@router.get("/{gdb_id}/layers", response_model=list[GDBLayerInfo])
async def get_gdb_layers(
    gdb_id: UUID,
    current_user: Annotated["User", Depends(CurrentActiveUser)] = None,
    session=Depends(get_session),
):
    """
    获取 GDB 文件中的所有图层信息。

    - **gdb_id**: GDB 文件 ID
    """
    # 查询数据库获取 GDB 文件记录
    statement = select(GDBFile).where(GDBFile.id == gdb_id, GDBFile.user_id == current_user.id)
    gdb_file = session.exec(statement).first()

    if not gdb_file:
        raise HTTPException(status_code=404, detail="GDB 文件不存在")

    # 调用 LFX 层的服务读取图层信息
    try:
        layers = gdb_service.read_gdb_layers(gdb_file.file_path)
        return layers
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取图层失败: {e}") from e


@router.get("/{gdb_id}/layer/{layer_name}", response_model=GDBLayerData)
async def get_layer_data(
    gdb_id: UUID,
    layer_name: str,
    limit: int = 100,
    offset: int = 0,
    current_user: Annotated["User", Depends(CurrentActiveUser)] = None,
    session=Depends(get_session),
):
    """
    获取指定图层的数据。

    - **gdb_id**: GDB 文件 ID
    - **layer_name**: 图层名称
    - **limit**: 返回要素数量限制（默认 100）
    - **offset**: 偏移量（默认 0）
    """
    # 查询数据库获取 GDB 文件记录
    statement = select(GDBFile).where(GDBFile.id == gdb_id, GDBFile.user_id == current_user.id)
    gdb_file = session.exec(statement).first()

    if not gdb_file:
        raise HTTPException(status_code=404, detail="GDB 文件不存在")

    # 调用 LFX 层的服务读取图层数据
    try:
        layer_data = gdb_service.read_layer_data(gdb_file.file_path, layer_name, limit, offset)
        return layer_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取图层数据失败: {e}") from e


@router.get("", response_model=list[GDBFileRead])
async def list_gdb_files(
    current_user: Annotated["User", Depends(CurrentActiveUser)] = None,
    session=Depends(get_session),
):
    """
    获取当前用户的所有 GDB 文件列表。
    """
    statement = select(GDBFile).where(GDBFile.user_id == current_user.id)
    gdb_files = session.exec(statement).all()
    return gdb_files


@router.delete("/{gdb_id}", status_code=204)
async def delete_gdb_file(
    gdb_id: UUID,
    current_user: Annotated["User", Depends(CurrentActiveUser)] = None,
    session=Depends(get_session),
):
    """
    删除 GDB 文件。

    - **gdb_id**: GDB 文件 ID
    """
    # 查询数据库获取 GDB 文件记录
    statement = select(GDBFile).where(GDBFile.id == gdb_id, GDBFile.user_id == current_user.id)
    gdb_file = session.exec(statement).first()

    if not gdb_file:
        raise HTTPException(status_code=404, detail="GDB 文件不存在")

    # 调用 LFX 层的服务删除存储文件
    gdb_service.delete_gdb_storage(str(gdb_id))

    # 删除数据库记录
    session.delete(gdb_file)
    session.commit()

    return None
```

### 步骤 6: Backend 层 - 路由注册

**文件路径**: `src/backend/base/langflow/api/v1/__init__.py`

```python
# 在文件顶部添加导入
from langflow.api.v1.gdb import router as gdb_router

# 在 __all__ 列表中添加
__all__ = [
    # ... 其他路由 ...
    "gdb_router",
]
```

**文件路径**: `src/backend/base/langflow/api/router.py`

```python
# 导入 GDB 路由
from langflow.api.v1 import gdb_router

# 注册路由
router_v1.include_router(gdb_router)
```

### 步骤 7: 数据库迁移

创建 Alembic 迁移脚本:

```bash
cd src/backend/base
uv run alembic revision --autogenerate -m "Add GDB file table"
uv run alembic upgrade head
```

---

## 5. 使用示例

### 5.1 完整的上传和读取流程

```python
# 客户端使用示例（Python requests）
import requests

# 1. 上传 GDB ZIP 文件
with open("FDMGENT1021.gdb.zip", "rb") as f:
    files = {"file": ("FDMGENT1021.gdb.zip", f, "application/zip")}
    data = {
        "name": "福建某市地块数据",
        "description": "地块要素数据"
    }
    response = requests.post(
        "http://localhost:7860/api/v1/gdb/upload",
        files=files,
        data=data,
        headers={"Blade-Auth": "your-token"}
    )
    gdb_file = response.json()
    gdb_id = gdb_file["id"]

# 2. 获取图层列表
response = requests.get(
    f"http://localhost:7860/api/v1/gdb/{gdb_id}/layers",
    headers={"Blade-Auth": "your-token"}
)
layers = response.json()
print(f"图层数量: {len(layers)}")
for layer in layers:
    print(f"- {layer['name']}: {layer['feature_count']} 个要素")

# 3. 读取第一个图层的数据
layer_name = layers[0]["name"]
response = requests.get(
    f"http://localhost:7860/api/v1/gdb/{gdb_id}/layer/{layer_name}",
    params={"limit": 10, "offset": 0},
    headers={"Blade-Auth": "your-token"}
)
layer_data = response.json()
print(f"字段: {layer_data['fields']}")
print(f"前2个要素: {layer_data['features'][:2]}")
```

### 5.2 直接使用 LFX 服务（Python 代码）

```python
from lfx.services.gdb import GDBService

# 创建服务实例
gdb_service = GDBService()

# 解压 GDB 文件
extract_result = gdb_service.extract_gdb_from_zip(
    zip_path="/path/to/file.gdb.zip",
    gdb_id="unique-id-123"
)

# 读取图层列表
layers = gdb_service.read_gdb_layers(extract_result.gdb_path)
for layer in layers:
    print(f"图层: {layer.name}, 要素数: {layer.feature_count}")

# 读取图层数据
layer_data = gdb_service.read_layer_data(
    gdb_path=extract_result.gdb_path,
    layer_name=layers[0].name,
    limit=10,
    offset=0
)

print(f"字段: {layer_data.fields}")
print(f"要素: {layer_data.features}")
```

---

## 6. 测试验证

### 6.1 LFX 层单元测试

**文件路径**: `src/lfx/tests/services/test_gdb_service.py`

```python
"""Tests for GDB service."""

import os
import tempfile
from pathlib import Path

import pytest

from lfx.services.gdb import GDBService


@pytest.fixture
def gdb_service():
    """Create a GDB service instance."""
    return GDBService()


def test_extract_gdb_from_zip(gdb_service):
    """Test extracting GDB from ZIP."""
    # 使用真实的测试 GDB ZIP 文件
    test_zip_path = "tests/data/sample.gdb.zip"
    gdb_id = "test-gdb-001"

    result = gdb_service.extract_gdb_from_zip(test_zip_path, gdb_id)

    assert os.path.exists(result.gdb_path)
    assert result.gdb_path.endswith(".gdb")
    assert result.layer_count > 0


def test_read_gdb_layers(gdb_service):
    """Test reading GDB layers."""
    # 使用已解压的测试 GDB 文件
    gdb_path = "tests/data/sample.gdb"
    layers = gdb_service.read_gdb_layers(gdb_path)

    assert len(layers) > 0
    assert all(layer.name for layer in layers)
    assert all(layer.feature_count >= 0 for layer in layers)


def test_read_layer_data(gdb_service):
    """Test reading layer data."""
    gdb_path = "tests/data/sample.gdb"
    layer_name = "test_layer"

    layer_data = gdb_service.read_layer_data(gdb_path, layer_name, limit=5)

    assert layer_data.layer_name == layer_name
    assert len(layer_data.fields) > 0
    assert len(layer_data.features) <= 5
```

### 6.2 Backend 层集成测试

**文件路径**: `src/backend/tests/integration/test_gdb_api.py`

```python
"""Integration tests for GDB API."""

from fastapi.testclient import TestClient

from langflow.main import create_app


def test_upload_gdb_file():
    """Test uploading a GDB file."""
    app = create_app()
    client = TestClient(app)

    with open("tests/data/sample.gdb.zip", "rb") as f:
        response = client.post(
            "/api/v1/gdb/upload",
            files={"file": ("sample.gdb.zip", f, "application/zip")},
            data={"name": "测试 GDB"}
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "测试 GDB"
    assert data["layer_count"] > 0
    assert "id" in data


def test_get_gdb_layers():
    """Test getting GDB layers."""
    # 先上传文件获取 ID
    app = create_app()
    client = TestClient(app)

    with open("tests/data/sample.gdb.zip", "rb") as f:
        upload_response = client.post(
            "/api/v1/gdb/upload",
            files={"file": ("sample.gdb.zip", f, "application/zip")},
        )

    gdb_id = upload_response.json()["id"]

    # 获取图层列表
    response = client.get(f"/api/v1/gdb/{gdb_id}/layers")

    assert response.status_code == 200
    layers = response.json()
    assert len(layers) > 0
    assert "name" in layers[0]
    assert "feature_count" in layers[0]
```

---

## 7. 注意事项

### 7.1 GDAL 安装

**系统库安装**:

```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev

# macOS
brew install gdal

# Windows
# 下载 OSGeo4W 安装器: https://trac.osgeo.org/osgeo4w/
```

**Python 绑定安装**:

```bash
# 使用 uv
uv pip install gdal

# 或使用 pip
pip install gdal
```

**验证安装**:

```python
from osgeo import gdal, ogr
print(f"GDAL version: {gdal.__version__}")
```

### 7.2 文件大小限制

在 FastAPI 中配置文件上传大小限制:

```python
# src/backend/base/langflow/main.py

from fastapi import FastAPI

app = FastAPI()

# 设置最大请求体大小（例如 100MB）
app.add_middleware(
    # 在 uvicorn 启动时添加 --limit-max-requests 参数
)
```

或在 uvicorn 启动时设置:

```bash
uvicorn --limit-max-requests 104857600 langflow.main:create_app
```

### 7.3 性能优化

1. **大文件处理**: 对于大型 GDB 文件，使用分页读取
2. **缓存**: 缓存图层列表信息，避免重复读取
3. **异步处理**: 对于耗时操作使用后台任务

```python
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_gdb_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    gdb_id = create_gdb_record()
    background_tasks.add_task(process_gdb_file, gdb_id, file)
    return {"id": gdb_id, "status": "processing"}
```

### 7.4 安全性

1. **文件验证**: 验证上传文件确实是有效的 GDB ZIP
2. **路径安全**: 防止路径遍历攻击
3. **文件隔离**: 每个用户的文件存储在独立目录
4. **清理策略**: 定期清理过期的临时文件

### 7.5 错误处理清单

- ✅ ZIP 文件损坏
- ✅ ZIP 中不包含 .gdb 目录
- ✅ GDB 文件损坏或格式不正确
- ✅ 图层不存在
- ✅ 权限不足（用户只能访问自己的文件）
- ✅ 磁盘空间不足
- ✅ GDAL 库未安装或版本不兼容

---

## 8. 后续扩展

### 8.1 可能的增强功能

1. **空间查询**:
   - 按边界框过滤要素
   - 空间关系查询（相交、包含等）

2. **坐标系统转换**:
   - 支持将数据转换为指定坐标系统
   - 常用坐标系统预设（WGS84、Web Mercator 等）

3. **数据导出**:
   - 导出为 GeoJSON
   - 导出为 Shapefile
   - 导出为 CSV

4. **预览功能**:
   - 生成地图缩略图
   - 简单的 Web 地图展示

5. **批量操作**:
   - 批量上传多个 GDB 文件
   - 批量导出

### 8.2 参考 AQMI 项目的高级功能

基于 AQMI 项目分析，可以考虑集成以下功能:

1. **影像处理** (参考 `aqmi/qt/project/geo_utils.py`):
   - 透明度检测
   - 图像裁剪和重投影
   - 多波段影像处理

2. **矢量化** (参考 `aqmi/extract/predict.py`):
   - 深度学习模型推理
   - 栅格转矢量
   - Shapefile 生成

3. **S3 集成** (参考 `aqmi/s3.py`):
   - 从 S3 读取 ZIP 文件
   - 处理结果直接上传到 S3

---

**文档版本**: v2.0
**最后更新**: 2025-12-16
**维护者**: Langflow Team

**架构说明**: 本实施方案严格遵循 Langflow 三层架构设计原则：
- **LFX 层**: 独立的核心业务逻辑，不依赖 Web 框架
- **Backend 层**: API 接口定义和数据库操作，调用 LFX 服务
