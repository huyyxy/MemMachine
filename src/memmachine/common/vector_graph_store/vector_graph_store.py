"""
向量图存储的抽象基类。

定义了添加、搜索和删除节点和边的接口。
"""

from abc import ABC, abstractmethod
from collections.abc import Collection, Mapping
from typing import Any
from uuid import UUID

from memmachine.common.embedder import SimilarityMetric

from .data_types import Edge, Node, Property


class VectorGraphStore(ABC):
    """
    向量图存储的抽象基类。
    """

    @abstractmethod
    async def add_nodes(self, nodes: Collection[Node]):
        """
        向图存储中添加节点。

        Args:
            nodes (Collection[Node]): 要添加的 Node 对象集合。
        """
        raise NotImplementedError

    @abstractmethod
    async def add_edges(self, edges: Collection[Edge]):
        """
        向图存储中添加边。

        Args:
            edges (Collection[Edge]): 要添加的 Edge 对象集合。
        """
        raise NotImplementedError

    @abstractmethod
    async def search_similar_nodes(
        self,
        query_embedding: list[float],
        embedding_property_name: str,
        similarity_metric: SimilarityMetric = SimilarityMetric.COSINE,
        limit: int | None = 100,
        required_labels: Collection[str] | None = None,
        required_properties: Mapping[str, Property] = {},
        include_missing_properties: bool = False,
    ) -> list[Node]:
        """
        搜索与查询嵌入向量相似的节点。

        Args:
            query_embedding (list[float]):
                用于比较的嵌入向量。
            embedding_property_name (str):
                存储嵌入向量的属性名称。
            similarity_metric (SimilarityMetric, optional):
                要使用的相似度度量方法
                (默认: SimilarityMetric.COSINE)。
            limit (int | None, optional):
                返回的最大相似节点数量。
                如果为 None，则返回尽可能多的相似节点
                (默认: 100)。
            required_labels (Collection[str] | None, optional):
                节点必须具有的标签集合。
                如果为 None，则不应用标签过滤。
            required_properties (Mapping[str, Property], optional):
                节点必须具有的属性名称到其必需值的映射。
                如果为空，则不应用属性过滤。
            include_missing_properties (bool, optional):
                如果为 True，缺少任何必需属性的节点
                也将包含在结果中。

        Returns:
            list[Node]:
                与查询嵌入向量相似的 Node 对象列表。
        """
        raise NotImplementedError

    @abstractmethod
    async def search_related_nodes(
        self,
        node_uuid: UUID,
        allowed_relations: Collection[str] | None = None,
        find_sources: bool = True,
        find_targets: bool = True,
        limit: int | None = None,
        required_labels: Collection[str] | None = None,
        required_properties: Mapping[str, Property] = {},
        include_missing_properties: bool = False,
    ) -> list[Node]:
        """
        通过边搜索与指定节点相关的节点。

        Args:
            node_uuid (UUID):
                要查找相关节点的节点的 UUID。
            allowed_relations (Collection[str] | None, optional):
                要考虑的关系类型集合。
                如果为 None，则考虑所有关系类型。
            find_sources (bool, optional):
                如果为 True，搜索作为指向指定节点的
                边的源节点的节点。
            find_targets (bool, optional):
                如果为 True，搜索作为从指定节点发出的
                边的目标节点的节点。
            limit (int | None, optional):
                返回的最大相关节点数量。
                如果为 None，则返回尽可能多的相关节点
                (默认: None)。
            required_labels (Collection[str] | None, optional):
                相关节点必须具有的标签集合。
                如果为 None，则不应用标签过滤。
            required_properties (Mapping[str, Property], optional):
                节点必须具有的属性名称到其必需值的映射。
                如果为空，则不应用属性过滤。
            include_missing_properties (bool, optional):
                如果为 True，缺少任何必需属性的节点
                也将包含在结果中。

        Returns:
            list[Node]:
                与指定节点相关的 Node 对象列表。
        """
        raise NotImplementedError

    @abstractmethod
    async def search_directional_nodes(
        self,
        by_property: str,
        start_at_value: Any | None = None,
        include_equal_start_at_value: bool = False,
        order_ascending: bool = True,
        limit: int | None = 1,
        required_labels: Collection[str] | None = None,
        required_properties: Mapping[str, Property] = {},
        include_missing_properties: bool = False,
    ) -> list[Node]:
        """
        按特定属性排序搜索节点。

        Args:
            by_property (str):
                用于排序节点的属性名称。
            start_at_value (Any | None, optional):
                搜索开始的值。
                如果为 None，根据 order_ascending
                从头或尾开始。
            include_equal_start_at_value (bool, optional):
                如果为 True，包含属性值等于
                start_at_value 的节点。
            order_ascending (bool, optional):
                如果为 True，按升序排列节点。
                如果为 False，按降序排列。
            limit (int | None, optional):
                返回的最大节点数量。
                如果为 None，则返回尽可能多的匹配节点
                (默认: 1)。
            required_labels (Collection[str] | None, optional):
                节点必须具有的标签集合。
                如果为 None，则不应用标签过滤。
            required_properties (Mapping[str, Property], optional):
                节点必须具有的属性名称到其必需值的映射。
                如果为空，则不应用属性过滤。
            include_missing_properties (bool, optional):
                如果为 True，缺少任何必需属性的节点
                也将包含在结果中。

        Returns:
            list[Node]:
                按指定属性排序的 Node 对象列表。
        """
        raise NotImplementedError

    @abstractmethod
    async def search_matching_nodes(
        self,
        limit: int | None = None,
        required_labels: Collection[str] | None = None,
        required_properties: Mapping[str, Property] = {},
        include_missing_properties: bool = False,
    ) -> list[Node]:
        """
        搜索匹配指定标签和属性的节点。

        Args:
            limit (int | None, optional):
                返回的最大节点数量。
                如果为 None，则返回尽可能多的匹配节点
                (默认: None)。
            required_labels (Collection[str] | None, optional):
                节点必须具有的标签集合。
                如果为 None，则不应用标签过滤。
            required_properties (Mapping[str, Property], optional):
                节点必须具有的属性名称到其必需值的映射。
                如果为空，则不应用属性过滤。
            include_missing_properties (bool, optional):
                如果为 True，缺少任何必需属性的节点
                也将包含在结果中。

        Returns:
            list[Node]:
                匹配指定条件的 Node 对象列表。
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_nodes(
        self,
        node_uuids: Collection[UUID],
    ):
        """
        从图存储中删除节点。

        Args:
            node_uuids (Collection[UUID]):
                要删除的节点的 UUID 集合。
        """
        raise NotImplementedError

    @abstractmethod
    async def clear_data(self):
        """
        清除图存储中的所有数据。
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        """
        关闭并释放资源。
        """
        raise NotImplementedError
