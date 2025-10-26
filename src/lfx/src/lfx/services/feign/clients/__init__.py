"""Feign clients."""

from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
from lfx.services.feign.clients.quality_model import QualityModelFeignClient

__all__ = [
    "DataConstructionFeignClient",
    "QualityModelFeignClient",
]
