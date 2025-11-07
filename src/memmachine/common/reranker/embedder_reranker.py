"""
基于嵌入模型的重新排序器实现。
"""

import numpy as np
from pydantic import BaseModel, Field, InstanceOf

from memmachine.common.embedder import Embedder, SimilarityMetric

from .reranker import Reranker


class EmbedderRerankerParams(BaseModel):
    """
    EmbedderReranker 的参数。

    属性:
        embedder (Embedder):
            嵌入器实例。
    """

    embedder: InstanceOf[Embedder] = Field(
        ..., description="用于生成嵌入向量的嵌入器实例"
    )


class EmbedderReranker(Reranker):
    """
    使用嵌入器对候选项与查询的相关性进行评分的重新排序器。
    """

    def __init__(self, params: EmbedderRerankerParams):
        """
        使用提供的配置初始化 EmbedderReranker。

        参数:
            params (EmbedderRerankerParams):
                EmbedderReranker 的参数。
        """
        super().__init__()

        self._embedder = params.embedder

    async def score(self, query: str, candidates: list[str]) -> list[float]:
        if len(candidates) == 0:
            return []

        query_embedding = np.array(await self._embedder.search_embed([query])).flatten()
        candidate_embeddings = np.array(await self._embedder.ingest_embed(candidates))

        match self._embedder.similarity_metric:
            case SimilarityMetric.COSINE:
                magnitude_products = np.linalg.norm(
                    candidate_embeddings, axis=-1
                ) * np.linalg.norm(query_embedding)
                magnitude_products[magnitude_products == 0] = float("inf")

                scores = (
                    np.dot(candidate_embeddings, query_embedding) / magnitude_products
                )
            case SimilarityMetric.DOT:
                scores = np.dot(candidate_embeddings, query_embedding)
            case SimilarityMetric.EUCLIDEAN:
                scores = -np.linalg.norm(
                    candidate_embeddings - query_embedding, axis=-1
                )
            case SimilarityMetric.MANHATTAN:
                scores = -np.sum(
                    np.abs(candidate_embeddings - query_embedding), axis=-1
                )
            case _:
                # 默认使用余弦相似度。
                magnitude_products = np.linalg.norm(
                    candidate_embeddings, axis=-1
                ) * np.linalg.norm(query_embedding)
                magnitude_products[magnitude_products == 0] = float("inf")

                scores = (
                    np.dot(candidate_embeddings, query_embedding) / magnitude_products
                )

        return scores.astype(float).tolist()
