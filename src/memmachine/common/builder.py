"""
基于资源定义和依赖关系构建资源的构建器的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import Any


class Builder(ABC):
    """
    基于资源定义和依赖关系构建资源的构建器的抽象基类。
    """

    @staticmethod
    @abstractmethod
    def get_dependency_ids(name: str, config: dict[str, Any]) -> set[str]:
        """
        获取构建该资源所需的依赖ID集合。

        参数:
            name (str):
                要构建的资源名称。
            config (dict[str, Any]):
                资源的配置字典。

        返回:
            set[str]:
                构建该资源所需的依赖ID集合。
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def build(name: str, config: dict[str, Any], injections: dict[str, Any]) -> Any:
        """
        基于资源名称、配置和注入的依赖关系构建资源。

        参数:
            name (str):
                要构建的资源名称。
            config (dict[str, Any]):
                资源的配置字典。
            injections (dict[str, Any]):
                注入的依赖项字典，其中键是依赖ID，值是相应的资源实例。
        """
        raise NotImplementedError
