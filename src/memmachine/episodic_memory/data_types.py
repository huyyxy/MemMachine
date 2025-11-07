from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

# JSON兼容数据结构的类型别名。
JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]


class ContentType(Enum):
    """Episode中内容类型的枚举。"""

    STRING = "string"
    # 可以在此添加其他内容类型，如'vector'、'image'等。


@dataclass
class SessionInfo:
    """
    表示单个对话会话的信息。
    通常从会话管理数据库中检索或存储。
    """

    group_id: str
    """群组对话的标识符。"""
    session_id: str
    """
    会话的唯一字符串标识符。
    """
    agent_ids: list[str]
    """参与会话的代理标识符列表。"""
    user_ids: list[str]
    """参与会话的用户标识符列表。"""
    configuration: dict
    """包含此会话的任何自定义配置的字典。"""


@dataclass
class GroupConfiguration:
    """
    表示一组对话的配置。
    """

    group_id: str
    """群的标识符。"""
    agent_list: list[str]
    """群中的代理标识符列表。"""
    user_list: list[str]
    """群中的用户标识符列表。"""
    configuration: dict
    """包含群组任何自定义配置的字典。"""


@dataclass
class MemoryContext:
    """
    定义内存实例的唯一上下文。
    用于隔离不同对话、用户和代理的内存。
    """

    group_id: str
    """群组上下文的标识符。"""
    agent_id: set[str]
    """上下文的代理标识符集合。"""
    user_id: set[str]
    """上下文的用户标识符集合。"""
    session_id: str
    """会话上下文的标识符。"""

    def __eq__(self, other):
        if not isinstance(other, MemoryContext):
            return False
        return self.group_id == other.group_id and self.session_id == other.session_id

    def __hash__(self):
        return hash(
            f"""{len(self.group_id)}#{self.group_id}_
            {len(self.session_id)}#{self.session_id}"""
        )


@dataclass(kw_only=True)
class Episode:
    """
    表示内存系统中的单个原子事件或数据片段。
    `kw_only=True` 强制在实例化时必须将所有字段指定为关键字参数，以提高清晰度。
    """

    uuid: UUID
    """Episode的唯一标识符（UUID）。"""
    episode_type: str
    """
    表示episode类型的字符串（例如，'message'、'thought'、'action'）。
    """
    content_type: ContentType
    """存储在'content'字段中的数据类型。"""
    content: Any
    """episode的实际数据，可以是任何类型。"""
    timestamp: datetime
    """episode发生的日期和时间。"""
    group_id: str
    """群的标识符（例如，特定的聊天室或私信）。"""
    session_id: str
    """此episode所属会话的标识符。"""
    producer_id: str
    """创建此episode的用户或代理的标识符。"""
    produced_for_id: str | None = None
    """目标接收者的标识符（如果有）。"""
    user_metadata: JSONValue = None
    """
    用于任何额外的用户定义元数据的字典，采用JSON兼容格式。"""
