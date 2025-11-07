"""
VectorGraphStore 实例的构建器。
"""

from typing import Any

from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field, SecretStr

from memmachine.common.builder import Builder

from .vector_graph_store import VectorGraphStore


class VectorGraphStoreBuilder(Builder):
    """
    VectorGraphStore 实例的构建器。
    """

    @staticmethod
    def get_dependency_ids(name: str, config: dict[str, Any]) -> set[str]:
        dependency_ids: set[str] = set()

        match name:
            case "neo4j":
                pass

        return dependency_ids

    @staticmethod
    def build(
        name: str, config: dict[str, Any], injections: dict[str, Any]
    ) -> VectorGraphStore:
        match name:
            case "neo4j":
                from .neo4j_vector_graph_store import (
                    Neo4jVectorGraphStore,
                    Neo4jVectorGraphStoreParams,
                )

                class Neo4jFactoryParams(BaseModel):
                    uri: str = Field(..., description="Neo4j 连接 URI")
                    username: str = Field(..., description="Neo4j 用户名")
                    password: SecretStr = Field(..., description="Neo4j 密码")
                    max_concurrent_transactions: int = Field(
                        100,
                        description="最大并发事务数",
                        gt=0,
                    )
                    force_exact_similarity_search: bool = Field(
                        False, description="是否强制精确相似度搜索"
                    )

                factory_params = Neo4jFactoryParams(**config)
                driver = AsyncGraphDatabase.driver(
                    factory_params.uri,
                    auth=(
                        factory_params.username,
                        factory_params.password.get_secret_value(),
                    ),
                )

                return Neo4jVectorGraphStore(
                    Neo4jVectorGraphStoreParams(
                        driver=driver,
                        max_concurrent_transactions=factory_params.max_concurrent_transactions,
                        force_exact_similarity_search=factory_params.force_exact_similarity_search,
                    )
                )
            case _:
                raise ValueError(f"未知的 VectorGraphStore 名称: {name}")
