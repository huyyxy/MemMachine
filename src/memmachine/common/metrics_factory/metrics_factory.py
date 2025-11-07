"""
指标工厂及其指标的抽象基类。

定义了创建和管理不同类型指标的接口，
例如计数器、仪表盘、直方图和摘要。
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable


class MetricsFactory(ABC):
    """
    指标工厂的抽象基类。
    """

    class Counter(ABC):
        """
        计数器指标的抽象基类。
        """

        @abstractmethod
        def increment(self, value: float = 1, labels: dict[str, str] = {}):
            """
            按指定值增加计数器。

            Args:
                value (float, optional):
                    增加计数器的数值（默认值: 1）。
                labels (dict[str, str], optional):
                    与增加操作关联的标签名值对。
                    如果为空，则不使用标签。
            """
            raise NotImplementedError

    class Gauge(ABC):
        """
        仪表盘指标的抽象基类。
        """

        @abstractmethod
        def set(self, value: float, labels: dict[str, str] = {}):
            """
            将仪表盘设置为指定值。

            Args:
                value (float):
                    要设置的仪表盘值。
                labels (dict[str, str], optional):
                    与设置操作关联的标签名值对。
                    如果为空，则不使用标签。
            """
            raise NotImplementedError

    class Histogram(ABC):
        """
        直方图指标的抽象基类。
        """

        @abstractmethod
        def observe(self, value: float, labels: dict[str, str] = {}):
            """
            观察一个值并将其记录到直方图中。

            Args:
                value (float):
                    要观察的值。
                labels (dict[str, str], optional):
                    与观察操作关联的标签名值对。
                    如果为空，则不使用标签。
            """
            raise NotImplementedError

    class Summary(ABC):
        """
        摘要指标的抽象基类。
        """

        @abstractmethod
        def observe(self, value: float, labels: dict[str, str] = {}):
            """
            观察一个值并将其记录到摘要中。

            Args:
                value (float):
                    要观察的值。
                labels (dict[str, str], optional):
                    与观察操作关联的标签名值对。
                    如果为空，则不使用标签。
            """
            raise NotImplementedError

    @abstractmethod
    def get_counter(
        self,
        name: str,
        description: str,
        label_names: Iterable[str] = (),
    ) -> Counter:
        """
        通过名称获取计数器指标，如果不存在则创建它。

        Args:
            name (str):
                计数器指标的名称。
            description (str):
                计数器指标的简要描述。
            label_names (Iterable[str], optional):
                计数器的标签名称的可迭代对象。
                如果为空，计数器将没有标签。

        Returns:
            Counter:
                计数器指标的实例。
        """
        raise NotImplementedError

    @abstractmethod
    def get_gauge(
        self,
        name: str,
        description: str,
        label_names: Iterable[str] = (),
    ) -> Gauge:
        """
        通过名称获取仪表盘指标，如果不存在则创建它。

        Args:
            name (str):
                仪表盘指标的名称。
            description (str):
                仪表盘指标的简要描述。
            label_names (Iterable[str], optional):
                仪表盘的标签名称的可迭代对象。
                如果为空，仪表盘将没有标签。

        Returns:
            Gauge:
                仪表盘指标的实例。
        """
        raise NotImplementedError

    @abstractmethod
    def get_histogram(
        self,
        name: str,
        description: str,
        label_names: Iterable[str] = (),
    ) -> Histogram:
        """
        通过名称获取直方图指标，如果不存在则创建它。

        Args:
            name (str):
                直方图指标的名称。
            description (str):
                直方图指标的简要描述。
            label_names (Iterable[str], optional):
                直方图的标签名称的可迭代对象。
                如果为空，直方图将没有标签。

        Returns:
            Histogram:
                直方图指标的实例。
        """
        raise NotImplementedError

    @abstractmethod
    def get_summary(
        self,
        name: str,
        description: str,
        label_names: Iterable[str] = (),
    ) -> Summary:
        """
        通过名称获取摘要指标，如果不存在则创建它。

        Args:
            name (str):
                摘要指标的名称。
            description (str):
                摘要指标的简要描述。
            label_names (Iterable[str], optional):
                摘要的标签名称的可迭代对象。
                如果为空，摘要将没有标签。

        Returns:
            Summary:
                摘要指标的实例。
        """
        raise NotImplementedError
