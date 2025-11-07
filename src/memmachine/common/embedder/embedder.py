"""
嵌入器的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import Any

from .data_types import SimilarityMetric


class Embedder(ABC):
    """
    嵌入器的抽象基类。
    """

    @abstractmethod
    async def ingest_embed(
        self,
        inputs: list[Any],
        max_attempts: int = 1,
    ) -> list[list[float]]:
        """
        为提供的输入生成嵌入。

        参数:
            inputs (list[Any]):
                要嵌入的输入列表。
            max_attempts (int):
                放弃前尝试的最大次数（默认：1）。

        返回:
            list[list[float]]:
                与每个输入对应的嵌入向量列表。

        抛出:
            ExternalServiceAPIError:
                来自底层嵌入 API 的错误。
            ValueError:
                无效的输入或 max_attempts。
            RuntimeError:
                其他错误的兜底异常。
        """
        raise NotImplementedError

    @abstractmethod
    async def search_embed(
        self,
        queries: list[Any],
        max_attempts: int = 1,
    ) -> list[list[float]]:
        """
        为提供的查询生成嵌入。

        参数:
            queries (list[Any]):
                要嵌入的查询列表。
            max_attempts (int):
                放弃前尝试的最大次数（默认：1）。

        返回:
            list[list[float]]:
                与每个查询对应的嵌入向量列表。

        抛出:
            ExternalServiceAPIError:
                来自底层嵌入 API 的错误。
            ValueError:
                无效的输入或 max_attempts。
            RuntimeError:
                其他错误的兜底异常。
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def model_id(self) -> str:
        """
        获取嵌入模型的标识符。
        标识符-维度对必须唯一。

        返回:
            str: 模型标识符。
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """
        获取此嵌入器生成的嵌入的维度数。

        返回:
            int: 维度数。
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def similarity_metric(self) -> SimilarityMetric:
        """
        获取此嵌入器生成的嵌入的相似度度量。

        返回:
            SimilarityMetric: 相似度度量。
        """
        raise NotImplementedError
