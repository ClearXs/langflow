"""GDB file service - Core business logic."""

import os
import shutil
import tempfile
import zipfile

from osgeo import gdal, ogr

from lfx.services.gdb.models import (
    GDBExtractResult,
    GDBFeature,
    GDBFieldInfo,
    GDBLayerData,
    GDBLayerInfo,
    GDBNodeType,
    GDBTreeNode,
    GDBTreeStructure,
)


class GDBService:
    """GDB 文件处理核心服务."""

    def __init__(self, storage_path: str | None = None):
        """初始化 GDB 服务.

        Args:
            storage_path: GDB 文件存储路径，默认使用系统临时目录
        """
        self.storage_path = storage_path or os.path.join(tempfile.gettempdir(), "langflow_gdb")
        os.makedirs(self.storage_path, exist_ok=True)

        # 启用 GDAL 异常
        gdal.UseExceptions()

    async def download_from_url(self, url: str) -> str:
        """从 MinIO URL 下载文件到临时目录.

        Args:
            url: MinIO 预签名 URL

        Returns:
            临时文件路径

        Raises:
            ValueError: 下载失败时抛出
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # 创建临时文件
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    suffix=".gdb.zip",
                    delete=False,
                    prefix="gdb_download_",
                ) as temp_file:
                    temp_file.write(response.content)
                    temp_file.flush()
                    temp_path = temp_file.name

                return temp_path

        except httpx.HTTPError as e:
            raise ValueError(f"从 MinIO 下载文件失败: {e}") from e

    def extract_gdb_from_zip(self, zip_path: str, gdb_id: str) -> GDBExtractResult:
        """从 ZIP 文件中解压 GDB.

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

        except Exception:
            # 清理失败的解压目录
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise

    def read_gdb_layers(self, gdb_path: str) -> list[GDBLayerInfo]:
        """读取 GDB 文件中的所有图层信息.

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
        """读取指定图层的数据.

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

            # 尝试获取字段数量，这一步可能触发 GDAL RuntimeError
            try:
                field_count = layer_defn.GetFieldCount()
            except RuntimeError as e:
                # GetFieldCount() 失败，说明这个图层无法被 OpenFileGDB 正确解析
                import traceback

                # 打印详细的调试信息
                print("\n" + "="*80)
                print("❌ GDAL RuntimeError 详细信息")
                print("="*80)
                print(f"图层名称: {layer_name}")
                print(f"GDB 路径: {gdb_path}")
                print(f"异常类型: {type(e).__name__}")
                print(f"异常消息: {e!s}")
                print(f"异常参数: {e.args}")

                # 打印完整的堆栈跟踪
                print("\n完整堆栈跟踪:")
                print("-" * 80)
                traceback.print_exc()
                print("-" * 80)

                # 获取 GDAL 最后的错误信息
                last_error = gdal.GetLastErrorMsg()
                last_error_type = gdal.GetLastErrorType()
                last_error_no = gdal.GetLastErrorNo()

                print("\nGDAL 错误详情:")
                print(f"  - Error Type: {last_error_type}")
                print(f"  - Error No: {last_error_no}")
                print(f"  - Error Message: {last_error}")

                # 尝试获取图层的更多信息
                print("\n图层元数据:")
                try:
                    geom_type = ogr.GeometryTypeToName(layer.GetGeomType())
                    feature_count = layer.GetFeatureCount(force=0)
                    print(f"  - 几何类型: {geom_type}")
                    print(f"  - 要素数量: {feature_count}")
                    srs = layer.GetSpatialRef()
                    if srs:
                        print(f"  - 空间参考: {srs.GetName()}")
                except Exception as meta_e:
                    print(f"  - 无法获取元数据: {meta_e}")

                print("="*80 + "\n")

                # 构造详细的警告信息
                warning_msg = (
                    f"此图层无法被 OpenFileGDB 驱动正确解析。\n"
                    f"GDAL 内部错误: {e!s}\n"
                    f"可能原因:\n"
                    f"  1. 使用了 Esri 专有的图层类型（如 Annotation、Dimension）\n"
                    f"  2. 包含 OpenFileGDB 不支持的字段类型\n"
                    f"  3. GDB 文件内部表结构异常\n"
                    f"建议: 在 ArcGIS/ArcMap 中将此图层导出为 Shapefile 或简化的 GDB 格式"
                )

                # 返回带警告的空数据，而不是直接抛出异常
                return GDBLayerData(
                    layer_name=layer_name,
                    fields=[],
                    features=[],
                    total_count=0,
                    warning=warning_msg,
                )

            for i in range(field_count):
                field_defn = layer_defn.GetFieldDefn(i)
                # 获取字段别名（备注）
                alias = field_defn.GetAlternativeName()
                if not alias:
                    alias = None
                fields.append(
                    GDBFieldInfo(
                        name=field_defn.GetName(),
                        alias=alias,
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

            # 判断是否需要添加警告信息
            warning = None
            field_count = layer_defn.GetFieldCount()
            if field_count == 0 and total_count == 0:
                warning = "此图层没有字段定义和要素数据。可能是 Annotation 图层、预留的空图层，或 OpenFileGDB 驱动不支持的特殊类型。"
            elif field_count == 0:
                warning = f"此图层没有字段定义，但有 {total_count} 个要素。可能是 OpenFileGDB 驱动不支持的特殊图层类型（如 Annotation）。"
            elif total_count == 0:
                warning = f"此图层有 {field_count} 个字段定义，但没有要素数据。这是一个空图层。"

            return GDBLayerData(
                layer_name=layer_name,
                fields=fields,
                features=features,
                total_count=total_count,
                warning=warning,
            )

        finally:
            # 释放资源
            data_source = None

    def delete_gdb_storage(self, gdb_id: str) -> None:
        """删除 GDB 存储目录.

        Args:
            gdb_id: GDB 唯一标识符
        """
        gdb_dir = os.path.join(self.storage_path, gdb_id)
        if os.path.exists(gdb_dir):
            shutil.rmtree(gdb_dir, ignore_errors=True)

    def get_gdb_path(self, gdb_id: str) -> str | None:
        """根据 GDB ID 获取 GDB 文件路径.

        Args:
            gdb_id: GDB 唯一标识符

        Returns:
            str | None: GDB 目录路径，如果不存在则返回 None
        """
        gdb_dir = os.path.join(self.storage_path, gdb_id)
        if not os.path.exists(gdb_dir):
            return None

        # 查找 .gdb 目录
        for root, dirs, _files in os.walk(gdb_dir):
            for dir_name in dirs:
                if dir_name.endswith(".gdb"):
                    return os.path.join(root, dir_name)

        return None

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

    def _build_layer_node(
        self,
        layer,
        parent_path: str,
        layer_name: str,
        include_data: bool = False,
        limit_per_layer: int = 100,
    ) -> GDBTreeNode:
        """构建单个图层节点（内部方法）.

        Args:
            layer: OGR Layer 对象
            parent_path: 父路径
            layer_name: 图层名称
            include_data: 是否包含图层数据
            limit_per_layer: 每个图层读取的记录数

        Returns:
            GDBTreeNode: 图层树节点
        """
        # 获取几何类型
        geom_type = layer.GetGeomType()
        geom_type_name = ogr.GeometryTypeToName(geom_type)

        # 判断是要素类还是表
        node_type = GDBNodeType.TABLE if geom_type == ogr.wkbNone else GDBNodeType.FEATURE_CLASS

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

        # 强制计算要素数量（force=1）
        # 某些 GDB 文件的元数据可能不准确，需要强制计算
        feature_count = layer.GetFeatureCount(force=1)

        # 读取图层数据
        layer_data = None
        if include_data:
            try:
                # 获取字段架构
                layer_defn = layer.GetLayerDefn()

                # 尝试获取字段数量，这一步可能触发 GDAL RuntimeError
                try:
                    field_count = layer_defn.GetFieldCount()
                except RuntimeError as e:
                    # GetFieldCount() 失败，说明这个图层无法被 OpenFileGDB 正确解析
                    print(f"❌ 无法获取图层 {layer_name} 的字段数量: {e}")
                    raise  # 重新抛出异常，让外层捕获

                print(f"[DEBUG] 图层 {layer_name}:")
                print(f"  - 字段数量: {field_count}")
                print(f"  - 要素数量: {feature_count}")
                print(f"  - 几何类型: {ogr.GeometryTypeToName(layer.GetGeomType())}")
                print(f"  - 图层路径: {parent_path}/{layer_name}")

                # 如果字段为 0，尝试诊断原因
                if field_count == 0:
                    print("  ⚠️  警告: 无法读取字段定义")
                    print("      可能原因: 图层使用了 OpenFileGDB 不支持的特性")
                    print("      建议: 在 ArcMap 中导出为简化格式")

                fields = []
                for i in range(field_count):
                    field_defn = layer_defn.GetFieldDefn(i)
                    alias = field_defn.GetAlternativeName()
                    if not alias:
                        alias = None
                    fields.append(
                        GDBFieldInfo(
                            name=field_defn.GetName(),
                            alias=alias,
                            type=field_defn.GetFieldTypeName(field_defn.GetType()),
                            width=field_defn.GetWidth(),
                        )
                    )

                print(f"  - 已读取 {len(fields)} 个字段定义")

                # 读取要素数据
                features = []
                layer.ResetReading()
                count = 0

                # 使用 try-except 保护要素读取，防止 GDAL 崩溃
                try:
                    while count < limit_per_layer:
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
                        for i in range(field_count):
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
                except RuntimeError as e:
                    # GDAL 底层错误，记录并继续
                    print(f"  ❌ GDAL 错误：无法读取要素数据 - {e}")
                    print("      这个图层可能使用了 OpenFileGDB 不支持的特性")

                print(f"  - 已读取 {len(features)} 个要素")

                # 判断是否需要添加警告信息
                warning = None
                if field_count == 0 and feature_count == 0:
                    warning = "此图层没有字段定义和要素数据。可能是 Annotation 图层、预留的空图层，或 OpenFileGDB 驱动不支持的特殊类型。"
                elif field_count == 0:
                    warning = f"此图层没有字段定义，但有 {feature_count} 个要素。可能是 OpenFileGDB 驱动不支持的特殊图层类型（如 Annotation）。"
                elif feature_count == 0:
                    warning = f"此图层有 {field_count} 个字段定义，但没有要素数据。这是一个空图层。"
                elif len(features) == 0 and feature_count > 0:
                    warning = f"此图层有 {feature_count} 个要素，但 OpenFileGDB 驱动无法读取要素数据。建议在 ArcMap 中导出为兼容格式。"

                # 使用已计算的 feature_count
                layer_data = GDBLayerData(
                    layer_name=layer_name,
                    fields=fields,
                    features=features,
                    total_count=feature_count,
                    warning=warning,
                )
            except RuntimeError as e:
                # 捕获 GDAL 底层错误，记录详细信息但不崩溃
                import traceback
                error_detail = traceback.format_exc()
                print(f"❌ GDAL RuntimeError：读取图层 {layer_name} 失败: {e}")
                print(f"详细错误:\n{error_detail}")

                # 返回空数据但带警告
                layer_data = GDBLayerData(
                    layer_name=layer_name,
                    fields=[],
                    features=[],
                    total_count=0,
                    warning=f"OpenFileGDB 驱动无法读取此图层（GDAL 错误）。建议在 ArcMap 中导出为兼容格式。错误: {str(e)[:100]}",
                )
            except Exception as e:
                # 如果读取数据失败，记录详细错误信息
                import traceback
                error_detail = traceback.format_exc()
                print(f"警告：读取图层 {layer_name} 数据失败: {e}")
                print(f"详细错误:\n{error_detail}")

                # 返回空数据但带警告
                layer_data = GDBLayerData(
                    layer_name=layer_name,
                    fields=[],
                    features=[],
                    total_count=0,
                    warning=f"读取图层数据失败: {str(e)[:100]}",
                )

        return GDBTreeNode(
            name=layer_name,
            node_type=node_type,
            path=f"{parent_path}/{layer_name}" if parent_path != "/" else f"/{layer_name}",
            feature_count=feature_count,
            geometry_type=geom_type_name,
            spatial_ref=srs_wkt,
            extent=extent,
            data=layer_data,
            children=[],
        )

    def read_gdb_tree_structure(
        self,
        gdb_path: str,
        include_data: bool = True,
        limit_per_layer: int = 100,
    ) -> GDBTreeStructure:
        """读取 GDB 文件的树形层次结构.

        使用 GDAL 3.1+ 的 GetRootGroup() API 解析 FeatureDataset 层次结构。

        Args:
            gdb_path: GDB 目录路径
            include_data: 是否包含每个图层的数据（默认 True）
            limit_per_layer: 每个图层读取的记录数（默认 100）

        Returns:
            GDBTreeStructure: GDB 树形结构

        Raises:
            ValueError: GDB 文件无效或 GDAL 版本不支持
        """
        # 打开数据源并获取根组
        ds = gdal.OpenEx(gdb_path, gdal.OF_VECTOR)
        if ds is None:
            raise ValueError(f"无法打开 GDB 文件: {gdb_path}")

        try:
            root_group = ds.GetRootGroup()
            if root_group is None:
                raise ValueError("无法获取 GDB 根组（需要 GDAL 3.1+）")

            # 创建根节点
            gdb_name = os.path.basename(gdb_path).replace(".gdb", "")
            root_node = GDBTreeNode(
                name=gdb_name,
                node_type=GDBNodeType.ROOT,
                path="/",
                children=[],
            )

            total_layers = 0
            total_datasets = 0

            # 获取根级图层（不在任何 FeatureDataset 中的图层）
            root_layer_names = root_group.GetVectorLayerNames()
            if root_layer_names:
                for layer_name in root_layer_names:
                    try:
                        layer = root_group.OpenVectorLayer(layer_name)
                        if layer:
                            layer_node = self._build_layer_node(
                                layer,
                                "/",
                                layer_name,
                                include_data=include_data,
                                limit_per_layer=limit_per_layer,
                            )
                            root_node.children.append(layer_node)
                            total_layers += 1
                    except RuntimeError as e:
                        # OpenVectorLayer 可能在打开某些图层时触发 GDAL 底层错误
                        print(f"⚠️  跳过无法打开的图层: {layer_name}")
                        print(f"   GDAL 错误: {e}")
                        # 创建一个带警告的空节点
                        error_node = GDBTreeNode(
                            name=layer_name,
                            node_type=GDBNodeType.FEATURE_CLASS,
                            path=f"/{layer_name}",
                            feature_count=0,
                            data=GDBLayerData(
                                layer_name=layer_name,
                                fields=[],
                                features=[],
                                total_count=0,
                                warning=f"无法打开此图层（GDAL 错误）: {str(e)[:100]}",
                            ),
                            children=[],
                        )
                        root_node.children.append(error_node)
                        total_layers += 1
                    except Exception as e:
                        # 捕获其他异常
                        print(f"⚠️  跳过图层 {layer_name}: {e}")
                        continue

            # 遍历 FeatureDatasets
            feature_datasets = root_group.GetGroupNames()
            total_datasets = len(feature_datasets) if feature_datasets else 0

            if feature_datasets:
                for dataset_name in feature_datasets:
                    dataset_group = root_group.OpenGroup(dataset_name)
                    if dataset_group is None:
                        continue

                    # 创建 FeatureDataset 节点
                    dataset_node = GDBTreeNode(
                        name=dataset_name,
                        node_type=GDBNodeType.FEATURE_DATASET,
                        path=f"/{dataset_name}",
                        children=[],
                    )

                    # 遍历 Dataset 内的图层
                    layer_names = dataset_group.GetVectorLayerNames()
                    if layer_names:
                        for layer_name in layer_names:
                            try:
                                layer = dataset_group.OpenVectorLayer(layer_name)
                                if layer:
                                    layer_node = self._build_layer_node(
                                        layer,
                                        f"/{dataset_name}",
                                        layer_name,
                                        include_data=include_data,
                                        limit_per_layer=limit_per_layer,
                                    )
                                    dataset_node.children.append(layer_node)
                                    total_layers += 1
                            except RuntimeError as e:
                                # OpenVectorLayer 可能在打开某些图层时触发 GDAL 底层错误
                                print(f"⚠️  跳过无法打开的图层: {dataset_name}/{layer_name}")
                                print(f"   GDAL 错误: {e}")
                                # 创建一个带警告的空节点
                                error_node = GDBTreeNode(
                                    name=layer_name,
                                    node_type=GDBNodeType.FEATURE_CLASS,
                                    path=f"/{dataset_name}/{layer_name}",
                                    feature_count=0,
                                    data=GDBLayerData(
                                        layer_name=layer_name,
                                        fields=[],
                                        features=[],
                                        total_count=0,
                                        warning=f"无法打开此图层（GDAL 错误）: {str(e)[:100]}",
                                    ),
                                    children=[],
                                )
                                dataset_node.children.append(error_node)
                                total_layers += 1
                            except Exception as e:
                                # 捕获其他异常
                                print(f"⚠️  跳过图层 {dataset_name}/{layer_name}: {e}")
                                continue

                    root_node.children.append(dataset_node)

            return GDBTreeStructure(
                gdb_name=gdb_name,
                gdb_path=gdb_path,
                total_layers=total_layers,
                total_datasets=total_datasets,
                root=root_node,
            )

        finally:
            ds = None
