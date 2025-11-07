from abc import ABC, abstractmethod
from typing import Any, Mapping

import numpy as np


class ProfileStorageBase(ABC):
    """
    配置存储的基类
    """

    @abstractmethod
    async def startup(self):
        """
        配置存储的初始化操作，
        例如创建数据库连接
        """
        raise NotImplementedError

    @abstractmethod
    async def cleanup(self):
        """
        配置存储的清理操作
        例如关闭数据库连接
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_all(self):
        """
        删除存储中的所有配置
        例如清空数据库表
        """
        raise NotImplementedError

    @abstractmethod
    async def get_profile(
        self,
        user_id: str,
        isolations: dict[str, bool | int | float | str] | None = None,
    ) -> dict[str, Any]:
        """
        根据ID获取配置
        返回: 每个特征和值的键值对列表。
           值是一个数组，包含：特征值、特征标签、是否已删除、更新时间、创建时间和删除时间。
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_profile(
        self,
        user_id: str,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        """
        根据ID删除所有配置
        """
        raise NotImplementedError

    @abstractmethod
    async def add_profile_feature(
        self,
        user_id: str,
        feature: str,
        value: str,
        tag: str,
        embedding: np.ndarray,
        metadata: dict[str, Any] | None = None,
        isolations: dict[str, bool | int | float | str] | None = None,
        citations: list[int] | None = None,
    ):
        """
        向配置中添加新特征
        """
        raise NotImplementedError

    @abstractmethod
    async def semantic_search(
        self,
        user_id: str,
        qemb: np.ndarray,
        k: int,
        min_cos: float,
        isolations: dict[str, bool | int | float | str] | None = None,
        include_citations: bool = False,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def delete_profile_feature_by_id(self, pid: int):
        raise NotImplementedError

    @abstractmethod
    async def get_all_citations_for_ids(
        self, pids: list[int]
    ) -> list[tuple[int, dict[str, bool | int | float | str]]]:
        raise NotImplementedError

    @abstractmethod
    async def delete_profile_feature(
        self,
        user_id: str,
        feature: str,
        tag: str,
        value: str | None = None,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        """
        从指定用户的配置中删除一个特征
        """
        raise NotImplementedError

    @abstractmethod
    async def get_large_profile_sections(
        self,
        user_id: str,
        thresh: int,
        isolations: dict[str, bool | int | float | str] | None = None,
    ) -> list[list[dict[str, Any]]]:
        """
        获取配置中至少包含thresh个条目的部分
        """
        raise NotImplementedError

    @abstractmethod
    async def add_history(
        self,
        user_id: str,
        content: str,
        metadata: dict[str, str] | None = None,
        isolations: dict[str, bool | int | float | str] | None = None,
    ) -> Mapping[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def delete_history(
        self,
        user_id: str,
        start_time: int = 0,
        end_time: int = 0,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        raise NotImplementedError

    @abstractmethod
    async def get_history_messages_by_ingestion_status(
        self,
        user_id: str,
        k: int = 0,
        is_ingested: bool = False,
    ) -> list[Mapping[str, Any]]:
        """
        根据摄入状态检索用户的历史消息列表
        如果k > 0，最多返回k条消息
        """
        raise NotImplementedError

    @abstractmethod
    async def get_uningested_history_messages_count(self) -> int:
        """
        检索未摄入的历史消息数量
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_messages_ingested(
        self,
        ids: list[int],
    ) -> None:
        """
        将指定ID的消息标记为已摄入
        """
        raise NotImplementedError

    @abstractmethod
    async def get_history_message(
        self,
        user_id: str,
        start_time: int = 0,
        end_time: int = 0,
        isolations: dict[str, bool | int | float | str] | None = None,
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def purge_history(
        self,
        user_id: str,
        start_time: int = 0,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        raise NotImplementedError
