"""
基于身份的重新排序器实现。
"""

from .reranker import Reranker


class IdentityReranker(Reranker):
    """
    返回候选项的原始顺序的重新排序器，
    不进行任何重新排序。
    """

    async def score(self, query: str, candidates: list[str]) -> list[float]:
        scores = list(map(float, reversed(range(len(candidates)))))
        return scores
