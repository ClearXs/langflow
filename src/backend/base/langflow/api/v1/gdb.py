"""GDB file API endpoints - Stateless implementation."""

import os
import tempfile
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

# 从 LFX 层导入核心服务
from lfx.services.gdb import GDBLayerData, GDBLayerInfo, GDBService, GDBTreeStructure
from pydantic import BaseModel, Field

router = APIRouter(prefix="/gdb", tags=["GDB"])


class ParseFromUrlRequest(BaseModel):
    """从 URL 解析 GDB 的请求模型."""

    minio_url: str = Field(..., description="MinIO 预签名 URL")

# 创建全局 GDB 服务实例
gdb_service = GDBService()


@router.post("/upload", status_code=201)
async def upload_gdb_file(
    file: UploadFile = File(..., description="GDB ZIP 文件"),
):
    """上传 GDB ZIP 文件并解压到临时目录.

    - **file**: .gdb.zip 格式的文件

    返回临时 GDB ID，用于后续查询图层信息和数据。
    """
    # 验证文件类型
    if not file.filename or not file.filename.endswith(".gdb.zip"):
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

        # 返回临时 GDB 信息
        return {
            "gdb_id": gdb_id,
            "name": extract_result.gdb_name,
            "file_path": extract_result.gdb_path,
            "file_size": file_size,
            "layer_count": extract_result.layer_count,
            "message": "GDB 文件上传成功，数据存储在临时目录中"
        }

    finally:
        # 清理临时 ZIP 文件
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@router.get("/{gdb_id}/layers", response_model=list[GDBLayerInfo])
async def get_gdb_layers(
    gdb_id: str,
):
    """获取 GDB 文件中的所有图层信息.

    - **gdb_id**: 上传时返回的临时 GDB ID
    """
    # 获取 GDB 文件路径
    gdb_path = gdb_service.get_gdb_path(gdb_id)

    if not gdb_path or not os.path.exists(gdb_path):
        raise HTTPException(status_code=404, detail="GDB 文件不存在或已过期")

    # 调用 LFX 层的服务读取图层信息
    try:
        layers = gdb_service.read_gdb_layers(gdb_path)
        return layers
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取图层失败: {e}") from e


@router.get("/{gdb_id}/layer/{layer_name}", response_model=GDBLayerData)
async def get_layer_data(
    gdb_id: str,
    layer_name: str,
    limit: int = 100,
    offset: int = 0,
):
    """获取指定图层的数据.

    - **gdb_id**: 上传时返回的临时 GDB ID
    - **layer_name**: 图层名称
    - **limit**: 返回要素数量限制（默认 100）
    - **offset**: 偏移量（默认 0）
    """
    # 获取 GDB 文件路径
    gdb_path = gdb_service.get_gdb_path(gdb_id)

    if not gdb_path or not os.path.exists(gdb_path):
        raise HTTPException(status_code=404, detail="GDB 文件不存在或已过期")

    # 调用 LFX 层的服务读取图层数据
    try:
        layer_data = gdb_service.read_layer_data(gdb_path, layer_name, limit, offset)
        return layer_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取图层数据失败: {e}") from e


@router.delete("/{gdb_id}", status_code=204)
async def delete_gdb_file(
    gdb_id: str,
):
    """删除临时 GDB 文件.

    - **gdb_id**: 上传时返回的临时 GDB ID
    """
    # 调用 LFX 层的服务删除存储文件
    try:
        gdb_service.delete_gdb_storage(gdb_id)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除 GDB 文件失败: {e}") from e


@router.post("/parse-from-url", response_model=GDBTreeStructure)
async def parse_gdb_from_minio_url(
    request: ParseFromUrlRequest,
):
    """从 MinIO URL 下载 GDB 文件并返回树形结构.

    完整流程：
    1. 从 MinIO URL 下载 ZIP 文件到临时目录
    2. 解压 GDB 文件
    3. 解析树形结构
    4. 返回结果
    5. 自动清理所有临时文件（ZIP 和 GDB 目录）

    - **minio_url**: MinIO 预签名 URL（指向 .gdb.zip 文件）

    返回 GDB 的完整树形层次结构，包含 FeatureDatasets 和图层信息。
    """
    temp_zip_path = None
    gdb_id = str(uuid4())

    try:
        # 1. 从 MinIO URL 下载文件
        try:
            temp_zip_path = await gdb_service.download_from_url(request.minio_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"下载文件失败: {e}") from e

        # 2. 解压 GDB 文件
        try:
            extract_result = gdb_service.extract_gdb_from_zip(temp_zip_path, gdb_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"解压文件失败: {e}") from e

        # 3. 读取树形结构
        try:
            tree_structure = gdb_service.read_gdb_tree_structure(
                extract_result.gdb_path,
                include_data=True,
                limit_per_layer=100,
            )
            return tree_structure
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            # GDAL 底层错误
            error_msg = str(e)
            if "filegdbtable.cpp" in error_msg or "openfilegdb" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"OpenFileGDB 驱动无法读取部分图层。建议：1) 使用 FileGDB 驱动，2) 在 ArcMap 中导出为兼容格式。原始错误: {error_msg}"
                ) from e
            raise HTTPException(status_code=500, detail=f"解析 GDB 文件失败: {error_msg}") from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"解析 GDB 文件失败: {e}") from e

    finally:
        # 4. 清理临时文件
        # 删除下载的 ZIP 文件
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.unlink(temp_zip_path)
            except Exception:
                # 忽略清理失败
                pass

        # 删除解压的 GDB 目录
        try:
            gdb_service.delete_gdb_storage(gdb_id)
        except Exception:
            # 忽略清理失败
            pass


class LayerDataFromUrlRequest(BaseModel):
    """从 URL 获取图层数据的请求模型."""

    minio_url: str = Field(..., description="MinIO 预签名 URL")
    layer_name: str = Field(..., description="图层名称")
    limit: int = Field(default=100, description="返回要素数量限制")
    offset: int = Field(default=0, description="偏移量")


@router.post("/layer-data-from-url", response_model=GDBLayerData)
async def get_layer_data_from_url(
    request: LayerDataFromUrlRequest,
):
    """从 MinIO URL 下载 GDB 文件并返回指定图层的数据.

    完整流程：
    1. 从 MinIO URL 下载 ZIP 文件到临时目录
    2. 解压 GDB 文件
    3. 读取指定图层的数据
    4. 返回数据
    5. 自动清理所有临时文件（ZIP 和 GDB 目录）

    - **minio_url**: MinIO 预签名 URL（指向 .gdb.zip 文件）
    - **layer_name**: 图层名称
    - **limit**: 返回要素数量限制（默认 100）
    - **offset**: 偏移量（默认 0）

    返回指定图层的完整数据，包含字段定义和要素列表。
    """
    temp_zip_path = None
    gdb_id = str(uuid4())

    try:
        # 1. 从 MinIO URL 下载文件
        try:
            temp_zip_path = await gdb_service.download_from_url(request.minio_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"下载文件失败: {e}") from e

        # 2. 解压 GDB 文件
        try:
            extract_result = gdb_service.extract_gdb_from_zip(temp_zip_path, gdb_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"解压文件失败: {e}") from e

        # 3. 读取图层数据
        try:
            layer_data = gdb_service.read_layer_data(
                extract_result.gdb_path,
                request.layer_name,
                request.limit,
                request.offset,
            )
            return layer_data
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except RuntimeError as e:
            # GDAL 底层错误（通常是驱动不支持）
            error_msg = str(e)
            if "filegdbtable.cpp" in error_msg or "openfilegdb" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"OpenFileGDB 驱动无法读取此图层。建议：1) 使用 FileGDB 驱动，2) 在 ArcMap 中导出为兼容格式。原始错误: {error_msg}"
                ) from e
            raise HTTPException(status_code=500, detail=f"读取图层数据失败: {error_msg}") from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取图层数据失败: {e}") from e

    finally:
        # 4. 清理临时文件
        # 删除下载的 ZIP 文件
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.unlink(temp_zip_path)
            except Exception:
                # 忽略清理失败
                pass

        # 删除解压的 GDB 目录
        try:
            gdb_service.delete_gdb_storage(gdb_id)
        except Exception:
            # 忽略清理失败
            pass
