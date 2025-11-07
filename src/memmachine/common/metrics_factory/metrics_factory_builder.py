"""
用于构建 MetricsFactory 实例的构建器。
"""

from typing import Any

from memmachine.common.builder import Builder

from .metrics_factory import MetricsFactory


class MetricsFactoryBuilder(Builder):
    """
    用于构建 MetricsFactory 实例的构建器。
    """

    @staticmethod
    def get_dependency_ids(name: str, config: dict[str, Any]) -> set[str]:
        dependency_ids: set[str] = set()

        match name:
            case "prometheus":
                pass

        return dependency_ids

    @staticmethod
    def build(
        name: str, config: dict[str, Any], injections: dict[str, Any]
    ) -> MetricsFactory:
        match name:
            case "prometheus":
                from .prometheus_metrics_factory import (
                    PrometheusMetricsFactory,
                )

                return PrometheusMetricsFactory()
            case _:
                raise ValueError(f"Unknown MetricsFactory name: {name}")
