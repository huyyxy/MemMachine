"""
基于句子转换器的嵌入器实现。
"""

import asyncio
import logging
import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, InstanceOf
from sentence_transformers import SentenceTransformer

from memmachine.common.data_types import ExternalServiceAPIError

from .data_types import SimilarityMetric
from .embedder import Embedder

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedderParams(BaseModel):
    """
    SentenceTransformerEmbedder 的参数。

    属性:
        model_name (str):
            句子转换器模型的名称。
        sentence_transformer (SentenceTransformer):
            用于生成嵌入的句子转换器模型。
    """

    model_name: str = Field(
        ..., description="句子转换器模型的名称。"
    )
    sentence_transformer: InstanceOf[SentenceTransformer] = Field(
        ...,
        description="用于生成嵌入的句子转换器模型。",
    )


class SentenceTransformerEmbedder(Embedder):
    """
    使用句子转换器模型为输入和查询生成嵌入的嵌入器。
    """

    def __init__(self, params: SentenceTransformerEmbedderParams):
        """
        使用提供的参数初始化 SentenceTransformerEmbedder。

        参数:
            params (SentenceTransformerEmbedderParams):
                SentenceTransformerEmbedder 的参数。
        """
        super().__init__()

        self._model_name = params.model_name
        self._sentence_transformer = params.sentence_transformer

        self._dimensions = (
            self._sentence_transformer.get_sentence_embedding_dimension()
            or len(self._sentence_transformer.encode(""))
        )
        match self._sentence_transformer.similarity_fn_name:
            case "cosine":
                self._similarity_metric = SimilarityMetric.COSINE
            case "dot":
                self._similarity_metric = SimilarityMetric.DOT
            case "euclidean":
                self._similarity_metric = SimilarityMetric.EUCLIDEAN
            case "manhattan":
                self._similarity_metric = SimilarityMetric.MANHATTAN
            case _:
                logger.warning(
                    "未知的相似度函数名称 '%s'，默认使用余弦相似度",
                    self._sentence_transformer.similarity_fn_name,
                )
                self._similarity_metric = SimilarityMetric.COSINE

    async def ingest_embed(
        self,
        inputs: list[Any],
        max_attempts: int = 1,
    ) -> list[list[float]]:
        return await self._embed(inputs, max_attempts)

    async def search_embed(
        self,
        queries: list[Any],
        max_attempts: int = 1,
    ) -> list[list[float]]:
        return await self._embed(queries, max_attempts, prompt_name="query")

    async def _embed(
        self,
        inputs: list[Any],
        max_attempts: int = 1,
        prompt_name: str | None = None,
    ) -> list[list[float]]:
        if not inputs:
            return []
        if max_attempts <= 0:
            raise ValueError("max_attempts must be a positive integer")

        embed_call_uuid = uuid4()

        start_time = time.monotonic()

        try:
            logger.debug(
                "[call uuid: %s] "
                "尝试使用 %s 句子转换器模型创建嵌入",
                embed_call_uuid,
                self._model_name,
            )
            response = await asyncio.to_thread(
                self._sentence_transformer.encode,
                inputs,
                prompt_name=prompt_name,
                show_progress_bar=False,
            )
        except Exception as e:
            # 异常可能无法重试。
            error_message = (
                f"[call uuid: {embed_call_uuid}] "
                f"由于假设为不可重试的 {type(e).__name__} 异常，放弃创建嵌入"
            )
            logger.error(error_message)
            raise ExternalServiceAPIError(error_message)

        end_time = time.monotonic()
        logger.debug(
            "[call uuid: %s] 嵌入在 %.3f 秒内创建完成",
            embed_call_uuid,
            end_time - start_time,
        )

        return response.astype(float).tolist()

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def similarity_metric(self) -> SimilarityMetric:
        return self._similarity_metric
