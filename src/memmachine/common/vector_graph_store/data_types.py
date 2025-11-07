"""
节点和边在向量图存储中的数据类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

# 可用作节点和边属性值的数据类型。
Property = (
    bool
    | int
    | float
    | str
    | datetime
    | list[bool]
    | list[int]
    | list[float]
    | list[str]
    | list[datetime]
    | None
)


@dataclass(kw_only=True)
class Node:
    uuid: UUID
    labels: set[str] = field(default_factory=set)
    properties: dict[str, Property] = field(default_factory=dict)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.uuid == other.uuid

    def __hash__(self):
        return hash(self.uuid)


@dataclass(kw_only=True)
class Edge:
    uuid: UUID
    source_uuid: UUID
    target_uuid: UUID
    relation: str = "RELATED_TO"
    properties: dict[str, Property] = field(default_factory=dict)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.uuid == other.uuid

    def __hash__(self):
        return hash(self.uuid)
