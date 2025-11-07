"""
重排序器的抽象基类。

定义了基于查询相关性对候选进行评分和重排序的接口。
"""

from abc import ABC, abstractmethod


class Reranker(ABC):
    """
    重排序器的抽象基类。
    """

    async def rerank(self, query: str, candidates: list[str]) -> list[str]:
        """
        根据候选与查询的相关性进行重排序。

        Args:
            query (str):
                输入的查询字符串。
            candidates (list[str]):
                待重排序的候选字符串列表。

        Returns:
            list[str]:
                重排序后的候选列表，按分数降序排列。
        """
        scores = await self.score(query, candidates)
        score_map = dict(zip(candidates, scores))

        return sorted(
            candidates,
            key=lambda candidate: score_map[candidate],
            reverse=True,
        )

    @abstractmethod
    async def score(self, query: str, candidates: list[str]) -> list[float]:
        """
        计算每个候选与查询的相关性分数。

        Args:
            query (str):
                输入的查询字符串。
            candidates (list[str]):
                待评分的候选字符串列表。

        Returns:
            list[float]:
                对应每个候选的分数列表。
        """
        raise NotImplementedError
