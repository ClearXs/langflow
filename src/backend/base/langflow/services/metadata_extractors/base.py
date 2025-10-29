"""元数据提取器基类

定义所有MetadataExtractor的通用接口。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langflow.graph.vertex.base import Vertex


class BaseMetadataExtractor(ABC):
    """元数据提取器抽象基类

    所有特定类型的MetadataExtractor都需要继承此类并实现：
    - extract_input_metadata(): 提取输入元信息
    - extract_output_metadata(): 提取输出元信息
    """

    def __init__(self, vertex: "Vertex"):
        """初始化元数据提取器

        Args:
            vertex: 顶点对象
        """
        self.vertex = vertex

    @abstractmethod
    async def extract_input_metadata(self) -> dict:
        """提取输入元信息

        在组件执行前调用，提取输入相关的元数据。

        Returns:
            输入元信息字典，例如：
            {
                "input_data": {...},
                "source_info": {...},
                ...
            }
        """

    @abstractmethod
    async def extract_output_metadata(
        self,
        results: dict | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        """提取输出元信息

        在组件执行后调用，提取输出相关的元数据。

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            输出元信息字典，例如：
            {
                "output_data": {...},
                "performance_metrics": {...},
                ...
            }
        """
