"""MemMachine 内存系统的 FastAPI 应用程序。

本模块设置并运行一个 FastAPI Web 服务器，提供与 Profile Memory 和 Episodic Memory 组件交互的端点。
它包括：
- 用于添加和搜索记忆的 API 端点。
- 与 FastMCP 的集成，用于将内存函数作为工具暴露给 LLM。
- 用于请求和响应验证的 Pydantic 模型。
- 用于初始化和清理资源（如数据库连接和内存管理器）的生命周期管理。
"""

import argparse
import asyncio
import copy
import logging
import os
from contextlib import asynccontextmanager
from importlib import import_module
from typing import Any, Self, cast

import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.params import Depends
from fastapi.responses import Response
from fastmcp import Context, FastMCP
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field, model_validator

from memmachine.common.embedder import EmbedderBuilder
from memmachine.common.language_model import LanguageModelBuilder
from memmachine.common.metrics_factory import MetricsFactoryBuilder
from memmachine.episodic_memory.data_types import ContentType
from memmachine.episodic_memory.episodic_memory import (
    AsyncEpisodicMemory,
    EpisodicMemory,
)
from memmachine.episodic_memory.episodic_memory_manager import (
    EpisodicMemoryManager,
)
from memmachine.profile_memory.profile_memory import ProfileMemory
from memmachine.profile_memory.prompt_provider import ProfilePrompt
from memmachine.profile_memory.storage.asyncpg_profile import AsyncPgProfileStorage

logger = logging.getLogger(__name__)


class AppConst:
    """应用程序和请求头键名的常量。"""

    DEFAULT_GROUP_ID = "default"
    """未提供时的默认组 ID 值。"""

    DEFAULT_SESSION_ID = "default"
    """未提供时的默认会话 ID 值。"""

    DEFAULT_USER_ID = "default"
    """未提供时的默认用户 ID 值。"""

    DEFAULT_PRODUCER_ID = "default"
    """未提供时的默认生产者 ID 值。"""

    DEFAULT_EPISODE_TYPE = "message"
    """未提供时的默认事件类型值。"""

    GROUP_ID_KEY = "group-id"
    """组 ID 的请求头键。"""

    SESSION_ID_KEY = "session-id"
    """会话 ID 的请求头键。"""

    AGENT_ID_KEY = "agent-id"
    """代理 ID 的请求头键。"""

    USER_ID_KEY = "user-id"
    """用户 ID 的请求头键。"""

    GROUP_ID_DOC = (
        "组或共享上下文的唯一标识符。"
        "用作主要过滤属性。"
        "对于单用户用例，可以与 `user_id` 相同。"
        "如果未提供且用户 ID 为空，则默认为 `default`。"
        "如果提供了用户 ID，则默认为第一个用户 ID。"
    )

    AGENT_ID_DOC = (
        "与此会话关联的代理标识符列表。"
        "如果多个 AI 代理参与同一上下文，则很有用。"
        "如果未提供，则默认为 `[]`。"
    )

    USER_ID_DOC = (
        "参与此会话的用户标识符列表。"
        "用于按用户隔离记忆和数据。"
        "如果未提供，则默认为 `['default']`。"
    )

    SESSION_ID_DOC = (
        "特定会话或对话的唯一标识符。"
        "可以表示聊天线程、Slack 频道或对话实例。"
        "每个对话应该是唯一的，以避免数据重叠。"
        "如果未提供且用户 ID 为空，则默认为 'default'。"
        "如果提供了用户 ID，则默认为第一个 `user_id`。"
    )

    PRODUCER_DOC = (
        "产生事件的实体标识符。"
        "如果未提供，则默认为会话中的第一个 `user_id`。"
        "如果 user_id 不可用，则默认为 `default`。"
    )

    PRODUCER_FOR_DOC = "为其产生事件的实体标识符。"

    EPISODE_CONTENT_DOC = "记忆事件的内容。"

    EPISODE_TYPE_DOC = "事件内容的类型（例如，消息）。"

    EPISODE_META_DOC = "事件的附加元数据。"

    GROUP_ID_EXAMPLES = ["group-1234", "project-alpha", "team-chat"]
    AGENT_ID_EXAMPLES = ["crm", "healthcare", "sales", "agent-007"]
    USER_ID_EXAMPLES = ["user-001", "alice@example.com"]
    SESSION_ID_EXAMPLES = ["session-5678", "chat-thread-42", "conversation-abc"]
    PRODUCER_EXAMPLES = ["chatbot", "user-1234", "agent-007"]
    PRODUCER_FOR_EXAMPLES = ["user-1234", "team-alpha", "project-xyz"]
    EPISODE_CONTENT_EXAMPLES = ["Met at the coffee shop to discuss project updates."]
    EPISODE_TYPE_EXAMPLES = ["message"]
    EPISODE_META_EXAMPLES = [{"mood": "happy", "location": "office"}]


# 请求会话数据
class SessionData(BaseModel):
    """用于组织和过滤记忆或对话上下文的元数据。

    每个 ID 服务于不同级别的数据分离：
    - `group_id`：标识共享上下文（例如，群聊或项目）。
    - `user_id`：标识组内的个人参与者。
    - `agent_id`：标识会话中涉及的 AI 代理。
    - `session_id`：标识特定的对话线程或会话。
    """

    group_id: str = Field(
        default="",
        description=AppConst.GROUP_ID_DOC,
        examples=AppConst.GROUP_ID_EXAMPLES,
    )

    agent_id: list[str] = Field(
        default=[],
        description=AppConst.AGENT_ID_DOC,
        examples=AppConst.AGENT_ID_EXAMPLES,
    )

    user_id: list[str] = Field(
        default=[],
        description=AppConst.USER_ID_DOC,
        examples=AppConst.USER_ID_EXAMPLES,
    )

    session_id: str = Field(
        default="",
        description=AppConst.SESSION_ID_DOC,
        examples=AppConst.SESSION_ID_EXAMPLES,
    )

    def merge(self, other: Self) -> None:
        """将另一个 SessionData 合并到此对象中（就地修改）。

        - 合并并去重列表字段。
        - 如果设置了新值，则覆盖字符串字段。
        """

        def merge_lists(a: list[str], b: list[str]) -> list[str]:
            if a and b:
                ret = list(dict.fromkeys(a + b))  # 保留顺序和唯一性
            else:
                ret = a or b
            return sorted(ret)

        if other.group_id and other.group_id != AppConst.DEFAULT_GROUP_ID:
            self.group_id = other.group_id

        if other.session_id and other.session_id != AppConst.DEFAULT_SESSION_ID:
            self.session_id = other.session_id

        if other.user_id == [AppConst.DEFAULT_USER_ID]:
            other.user_id = []

        self.agent_id = merge_lists(self.agent_id, other.agent_id)
        self.user_id = merge_lists(self.user_id, other.user_id)

    def first_user_id(self) -> str:
        """如果可用则返回第一个用户 ID，否则返回默认用户 ID。"""
        return self.user_id[0] if self.user_id else AppConst.DEFAULT_USER_ID

    def combined_user_ids(self) -> str:
        """将组 ID 格式化为 <size>#<user-id><size>#<user-id>..."""
        return "".join([f"{len(uid)}#{uid}" for uid in sorted(self.user_id)])

    def from_user_id_or(self, default_value: str) -> str:
        """返回第一个用户 ID 或组合的用户 ID 作为默认字符串。"""
        size_user_id = len(self.user_id)
        if size_user_id == 0:
            return default_value
        elif size_user_id == 1:
            return self.first_user_id()
        else:
            return self.combined_user_ids()

    @model_validator(mode="after")
    def _set_default_group_id(self) -> Self:
        """如果未设置，则将 group_id 默认为默认组。"""
        if not self.group_id:
            self.group_id = self.from_user_id_or(AppConst.DEFAULT_GROUP_ID)
        return self

    @model_validator(mode="after")
    def _set_default_session_id(self) -> Self:
        """如果未设置，则将 session_id 默认为 'default'。"""
        if not self.session_id:
            self.session_id = self.from_user_id_or(AppConst.DEFAULT_SESSION_ID)
        return self

    @model_validator(mode="after")
    def _set_default_user_id(self) -> Self:
        """如果未设置，则将 user_id 默认为 ['default']。"""
        if len(self.user_id) == 0 and len(self.agent_id) == 0:
            self.user_id = [AppConst.DEFAULT_USER_ID]
        else:
            self.user_id = sorted(self.user_id)
        return self

    def is_valid(self) -> bool:
        """如果会话数据无效（group_id 和 session_id 都为空），则返回 False，否则返回 True。
        """
        return (
            self.group_id != "" and self.session_id != "" and self.first_user_id() != ""
        )


class RequestWithSession(BaseModel):
    """包含会话数据的请求的基类。"""

    session: SessionData | None = Field(
        None,
        deprecated=True,
        description="请求体中的 session 字段已弃用。"
        "请改用基于请求头的会话。",
    )

    def log_error_with_session(self, e: HTTPException, message: str):
        sess = self.get_session()
        session_name = (
            f"{sess.group_id}-{sess.agent_id}-{sess.user_id}-{sess.session_id}"
        )
        logger.error(f"{message} for %s", session_name)
        logger.error(e)

    def get_session(self) -> SessionData:
        if self.session is None:
            return SessionData(
                group_id="",
                agent_id=[],
                user_id=[],
                session_id="",
            )
        return self.session

    def new_404_not_found_error(self, message: str):
        session = self.get_session()
        return HTTPException(
            status_code=404,
            detail=f"{message} for {session.user_id},"
            f"{session.session_id},"
            f"{session.group_id},"
            f"{session.agent_id}",
        )

    def merge_session(self, session: SessionData) -> None:
        """将另一个 SessionData 合并到此对象中（就地修改）。

        - 合并并去重列表字段。
        - 如果设置了新值，则覆盖字符串字段。
        """
        if self.session is None:
            self.session = session
        else:
            self.session.merge(session)

    def validate_session(self) -> None:
        """验证会话数据不为空。
        抛出:
            RequestValidationError: 如果会话数据为空。
        """
        if self.session is None or not self.session.is_valid():
            # 抛出与 FastAPI 使用的相同类型的验证错误
            raise RequestValidationError(
                [
                    {
                        "loc": ["header", "session"],
                        "msg": "group_id or session_id cannot be empty",
                        "type": "value_error.missing",
                    }
                ]
            )

    def merge_and_validate_session(self, other: SessionData) -> None:
        """将另一个 SessionData 合并到此对象中并验证（就地修改）。

        - 合并并去重列表字段。
        - 如果设置了新值，则覆盖字符串字段。
        - 验证结果会话数据不为空。

        抛出:
            RequestValidationError: 如果结果会话数据为空。
        """
        self.merge_session(other)
        self.validate_session()

    def update_response_session_header(self, response: Response | None) -> None:
        """使用会话数据更新响应头。"""
        if response is None:
            return
        sess = self.get_session()
        if sess.group_id:
            response.headers[AppConst.GROUP_ID_KEY] = sess.group_id
        if sess.session_id:
            response.headers[AppConst.SESSION_ID_KEY] = sess.session_id
        if sess.agent_id:
            response.headers[AppConst.AGENT_ID_KEY] = ",".join(sess.agent_id)
        if sess.user_id:
            response.headers[AppConst.USER_ID_KEY] = ",".join(sess.user_id)


# === 请求模型 ===
class NewEpisode(RequestWithSession):
    """添加新记忆事件的请求模型。"""

    producer: str = Field(
        default="",
        description=AppConst.PRODUCER_DOC,
        examples=AppConst.PRODUCER_EXAMPLES,
    )

    produced_for: str = Field(
        default="",
        description=AppConst.PRODUCER_FOR_DOC,
        examples=AppConst.PRODUCER_FOR_EXAMPLES,
    )

    episode_content: str | list[float] = Field(
        default="",
        description=AppConst.EPISODE_CONTENT_DOC,
        examples=AppConst.EPISODE_CONTENT_EXAMPLES,
    )

    episode_type: str = Field(
        default=AppConst.DEFAULT_EPISODE_TYPE,
        description=AppConst.EPISODE_TYPE_DOC,
        examples=AppConst.EPISODE_TYPE_EXAMPLES,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=AppConst.EPISODE_META_DOC,
        examples=AppConst.EPISODE_META_EXAMPLES,
    )

    @model_validator(mode="after")
    def _set_default_producer_id(self) -> Self:
        """如果未设置，则将 producer 默认为第一个用户 ID 或 'default'。"""
        if self.producer == "":
            if self.session is not None:
                self.producer = self.session.from_user_id_or("")
        if self.producer == "":
            self.producer = AppConst.DEFAULT_PRODUCER_ID
        return self


class SearchQuery(RequestWithSession):
    """搜索记忆的请求模型。"""

    query: str
    filter: dict[str, Any] | None = None
    limit: int | None = None


def _split_str_to_list(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip() != ""]


async def _get_session_from_header(
    request: Request,
    group_id: str = Header(
        AppConst.DEFAULT_GROUP_ID,
        alias=AppConst.GROUP_ID_KEY,
        description=AppConst.GROUP_ID_DOC,
        examples=AppConst.GROUP_ID_EXAMPLES,
    ),
    session_id: str = Header(
        AppConst.DEFAULT_SESSION_ID,
        alias=AppConst.SESSION_ID_KEY,
        description=AppConst.SESSION_ID_DOC,
        examples=AppConst.SESSION_ID_EXAMPLES,
    ),
    agent_id: str = Header(
        "",
        alias=AppConst.AGENT_ID_KEY,
        description=AppConst.AGENT_ID_DOC,
        examples=AppConst.AGENT_ID_EXAMPLES,
    ),
    user_id: str = Header(
        "",
        alias=AppConst.USER_ID_KEY,
        description=AppConst.USER_ID_DOC,
        examples=AppConst.USER_ID_EXAMPLES,
    ),
) -> SessionData:
    """从请求头提取会话数据并返回 SessionData 对象。"""
    group_id_keys = [AppConst.GROUP_ID_KEY, "group_id"]
    session_id_keys = [AppConst.SESSION_ID_KEY, "session_id"]
    agent_id_keys = [AppConst.AGENT_ID_KEY, "agent_id"]
    user_id_keys = [AppConst.USER_ID_KEY, "user_id"]
    headers = request.headers

    def get_with_alias(possible_keys: list[str], default: str):
        for key in possible_keys:
            for hk, hv in headers.items():
                if hk.lower() == key.lower():
                    return hv
        return default

    group_id = get_with_alias(group_id_keys, group_id)
    session_id = get_with_alias(session_id_keys, session_id)
    agent_id = get_with_alias(agent_id_keys, agent_id)
    user_id = get_with_alias(user_id_keys, user_id)
    return SessionData(
        group_id=group_id,
        session_id=session_id,
        agent_id=_split_str_to_list(agent_id),
        user_id=_split_str_to_list(user_id),
    )


# === 响应模型 ===
class SearchResult(BaseModel):
    """记忆搜索结果的响应模型。"""

    status: int = 0
    content: dict[str, Any]


class MemorySession(BaseModel):
    """会话信息的响应模型。"""

    user_ids: list[str]
    session_id: str
    group_id: str | None
    agent_ids: list[str] | None


class AllSessionsResponse(BaseModel):
    """列出所有会话的响应模型。"""

    sessions: list[MemorySession]


class DeleteDataRequest(RequestWithSession):
    """删除会话所有数据的请求模型。"""

    pass


# === 全局变量 ===
# 内存管理器的全局实例，在应用程序启动时初始化。
profile_memory: ProfileMemory | None = None
episodic_memory: EpisodicMemoryManager | None = None


# === 生命周期管理 ===


async def initialize_resource(
    config_file: str,
) -> tuple[EpisodicMemoryManager, ProfileMemory]:
    """
    这是一个临时解决方案，用于统一 ProfileMemory 和 Episodic Memory 的配置。
    初始化 ProfileMemory 和 EpisodicMemoryManager 实例，
    并建立必要的连接（例如，到数据库）。
    这些资源在关闭时会被清理。
    参数:
        config_file: 配置文件的路径。
    返回:
        包含 EpisodicMemoryManager 和 ProfileMemory 实例的元组。
    """

    try:
        yaml_config = yaml.safe_load(open(config_file, encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件 {config_file} 未找到")
    except yaml.YAMLError:
        raise ValueError(f"配置文件 {config_file} 不是有效的 YAML")
    except Exception as e:
        raise e

    def config_to_lowercase(data: Any) -> Any:
        """递归地将嵌套结构中的所有字典键转换为小写。"""
        if isinstance(data, dict):
            return {k.lower(): config_to_lowercase(v) for k, v in data.items()}
        if isinstance(data, list):
            return [config_to_lowercase(i) for i in data]
        return data

    yaml_config = config_to_lowercase(yaml_config)

    # 如果配置中定义了模型，则使用它。
    profile_config = yaml_config.get("profile_memory", {})

    # 从配置创建 LLM 模型
    model_config = yaml_config.get("model", {})

    model_name = profile_config.get("llm_model")
    if model_name is None:
        raise ValueError("配置文件中未为 profile memory 配置模型")

    model_def = model_config.get(model_name)
    if model_def is None:
        raise ValueError(f"无法找到模型 {model_name} 的定义")

    profile_model = copy.deepcopy(model_def)
    metrics_manager = MetricsFactoryBuilder.build("prometheus", {}, {})
    profile_model["metrics_factory_id"] = "prometheus"
    metrics_injection = {}
    metrics_injection["prometheus"] = metrics_manager
    model_vendor = profile_model.pop("model_vendor")
    llm_model = LanguageModelBuilder.build(
        model_vendor, profile_model, metrics_injection
    )

    # 创建嵌入器
    embedders = yaml_config.get("embedder", {})
    embedder_id = profile_config.get("embedding_model")
    if embedder_id is None:
        raise ValueError(
            "配置文件中未为 profile memory 配置嵌入模型"
        )

    embedder_def = embedders.get(embedder_id)
    if embedder_def is None:
        raise ValueError(f"无法找到嵌入器 {embedder_id} 的定义")

    embedder_config = copy.deepcopy(embedder_def["config"])
    if embedder_def["name"] == "openai":
        embedder_config["metrics_factory_id"] = "prometheus"

    embeddings = EmbedderBuilder.build(
        embedder_def["name"], embedder_config, metrics_injection
    )

    # 获取数据库配置
    # 如果配置文件中可用，则从配置文件获取数据库配置
    db_config_name = profile_config.get("database")
    if db_config_name is None:
        raise ValueError("配置文件中未配置 Profile 数据库")
    db_config = yaml_config.get("storage", {})
    db_config = db_config.get(db_config_name)
    if db_config is None:
        raise ValueError(f"无法找到数据库 {db_config_name} 的配置")

    prompt_file = profile_config.get("prompt", "profile_prompt")
    prompt_module = import_module(f".prompt.{prompt_file}", __package__)
    profile_prompt = ProfilePrompt.load_from_module(prompt_module)

    profile_storage = AsyncPgProfileStorage.build_config(
        {
            "host": db_config.get("host", "localhost"),
            "port": db_config.get("port", 0),
            "user": db_config.get("user", ""),
            "password": db_config.get("password", ""),
            "database": db_config.get("database", ""),
        }
    )

    profile_memory = ProfileMemory(
        model=llm_model,
        embeddings=embeddings,
        profile_storage=profile_storage,
        prompt=profile_prompt,
    )
    episodic_memory = EpisodicMemoryManager.create_episodic_memory_manager(config_file)
    return episodic_memory, profile_memory


@asynccontextmanager
async def http_app_lifespan(application: FastAPI):
    """处理应用程序启动和关闭事件。

    初始化 ProfileMemory 和 EpisodicMemoryManager 实例，
    并建立必要的连接（例如，到数据库）。
    这些资源在关闭时会被清理。

    参数:
        application: FastAPI 应用程序实例。
    """
    config_file = os.getenv("MEMORY_CONFIG", "cfg.yml")

    global episodic_memory
    global profile_memory
    episodic_memory, profile_memory = await initialize_resource(config_file)
    await profile_memory.startup()
    yield
    await profile_memory.cleanup()
    await episodic_memory.shut_down()


mcp = FastMCP("MemMachine")
mcp_app = mcp.http_app("/")


@asynccontextmanager
async def mcp_http_lifespan(application: FastAPI):
    """管理主应用程序和 MCP 应用程序的合并生命周期。

    此上下文管理器链接 `http_app_lifespan`（用于主应用程序资源，如内存管理器）
    和 `mcp_app.lifespan`（用于 MCP 特定资源）。它确保所有资源在启动时初始化
    并在关闭时按正确顺序清理。

    参数:
        application: FastAPI 应用程序实例。
    """
    async with http_app_lifespan(application):
        async with mcp_app.lifespan(application):
            yield


app = FastAPI(lifespan=mcp_http_lifespan)
app.mount("/mcp", mcp_app)


@mcp.tool()
async def mcp_add_session_memory(episode: NewEpisode) -> dict[str, Any]:
    """用于为特定会话添加记忆事件的 MCP 工具。它将事件添加到情景记忆和档案记忆。

    此工具不需要上下文中预先存在的开放会话。
    它直接使用 `NewEpisode` 对象中提供的会话数据添加记忆事件。

    参数:
        episode: 完整的新事件数据，包括会话信息。

    返回:
        如果成功添加记忆，则状态为 0，否则状态为 -1 并包含错误消息。
    """
    try:
        await _add_memory(episode)
    except HTTPException as e:
        episode.log_error_with_session(e, "Failed to add memory episode")
        return {"status": -1, "error_msg": str(e)}
    return {"status": 0, "error_msg": ""}


@mcp.tool()
async def mcp_add_episodic_memory(episode: NewEpisode) -> dict[str, Any]:
    """用于为特定会话添加记忆事件的 MCP 工具。它仅将事件添加到情景记忆。

    此工具不需要上下文中预先存在的开放会话。
    它直接使用 `NewEpisode` 对象中提供的会话数据添加记忆事件。

    参数:
        episode: 完整的新事件数据，包括会话信息。

    返回:
        如果成功添加记忆，则状态为 0，否则状态为 -1 并包含错误消息。
    """
    try:
        await _add_episodic_memory(episode)
    except HTTPException as e:
        episode.log_error_with_session(e, "Failed to add memory episode")
        return {"status": -1, "error_msg": str(e)}
    return {"status": 0, "error_msg": ""}


@mcp.tool()
async def mcp_add_profile_memory(episode: NewEpisode) -> dict[str, Any]:
    """用于为特定会话添加记忆事件的 MCP 工具。它仅将事件添加到档案记忆。

    此工具不需要上下文中预先存在的开放会话。
    它直接使用 `NewEpisode` 对象中提供的会话数据添加记忆事件。

    参数:
        episode: 完整的新事件数据，包括会话信息。

    返回:
        如果成功添加记忆，则状态为 0，否则状态为 -1 并包含错误消息。
    """
    try:
        await _add_profile_memory(episode)
    except HTTPException as e:
        sess = episode.get_session()
        session_name = f"""{sess.group_id}-{sess.agent_id}-
                           {sess.user_id}-{sess.session_id}"""
        logger.error("Failed to add memory episode for %s", session_name)
        logger.error(e)
        return {"status": -1, "error_msg": str(e)}
    return {"status": 0, "error_msg": ""}


@mcp.tool()
async def mcp_search_episodic_memory(q: SearchQuery) -> SearchResult:
    """在特定会话中搜索情景记忆的 MCP 工具。
    此工具不需要上下文中预先存在的开放会话。
    它仅搜索情景记忆以查找提供的查询。

    参数:
        q: 搜索查询。

    返回:
        如果成功，则返回 SearchResult 对象，否则返回 None。
    """
    return await _search_episodic_memory(q)


@mcp.tool()
async def mcp_search_profile_memory(q: SearchQuery) -> SearchResult:
    """在特定会话中搜索档案记忆的 MCP 工具。
    此工具不需要上下文中预先存在的开放会话。
    它仅搜索档案记忆以查找提供的查询。

    参数:
        q: 搜索查询。

    返回:
        如果成功，则返回 SearchResult 对象，否则返回 None。
    """
    return await _search_profile_memory(q)


@mcp.tool()
async def mcp_search_session_memory(q: SearchQuery) -> SearchResult:
    """在特定会话中搜索记忆的 MCP 工具。

    此工具不需要上下文中预先存在的开放会话。
    它在情景记忆和档案记忆中搜索提供的查询。

    参数:
        q: 搜索查询。

    返回:
        如果成功，则返回 SearchResult 对象，否则返回 None。
    """
    return await _search_memory(q)


@mcp.tool()
async def mcp_delete_session_data(sess: SessionData) -> dict[str, Any]:
    """删除特定会话的所有数据的 MCP 工具。

    此工具不需要上下文中预先存在的开放会话。
    它删除与提供的会话数据关联的所有数据。

    参数:
        sess: 要删除所有记忆的会话数据。

    返回:
        如果删除成功，则状态为 0，否则状态为 -1 并包含错误消息。
    """
    try:
        await _delete_session_data(DeleteDataRequest(session=sess))
    except HTTPException as e:
        session_name = f"""{sess.group_id}-{sess.agent_id}-
                           {sess.user_id}-{sess.session_id}"""
        logger.error("Failed to add memory episode for %s", session_name)
        logger.error(e)
        return {"status": -1, "error_msg": str(e)}
    return {"status": 0, "error_msg": ""}


@mcp.tool()
async def mcp_delete_data(ctx: Context) -> dict[str, Any]:
    """删除当前会话的所有数据的 MCP 工具。

    此工具需要开放的记忆会话。它删除与 MCP 上下文中存储的会话关联的所有数据。

    参数:
        ctx: MCP 上下文。

    返回:
        如果删除成功，则状态为 0，否则状态为 -1 并包含错误消息。
    """
    try:
        sess = ctx.get_state("session_data")
        if sess is None:
            return {"status": -1, "error_msg": "No session open"}
        delete_data_req = DeleteDataRequest(session=sess)
        await _delete_session_data(delete_data_req)
    except HTTPException as e:
        session_name = f"""{sess.group_id}-{sess.agent_id}-
                           {sess.user_id}-{sess.session_id}"""
        logger.error("Failed to add memory episode for %s", session_name)
        logger.error(e)
        return {"status": -1, "error_msg": str(e)}
    return {"status": 0, "error_msg": ""}


@mcp.resource("sessions://sessions")
async def mcp_get_sessions() -> AllSessionsResponse:
    """检索所有记忆会话的 MCP 资源。

    返回:
        包含所有会话列表的 AllSessionsResponse。
    """
    return await get_all_sessions()


@mcp.resource("users://{user_id}/sessions")
async def mcp_get_user_sessions(user_id: str) -> AllSessionsResponse:
    """检索特定用户的所有会话的 MCP 资源。

    返回:
        包含该用户会话列表的 AllSessionsResponse。
    """
    return await get_sessions_for_user(user_id)


@mcp.resource("groups://{group_id}/sessions")
async def mcp_get_group_sessions(group_id: str) -> AllSessionsResponse:
    """检索特定组的所有会话的 MCP 资源。

    返回:
        包含该组会话列表的 AllSessionsResponse。
    """
    return await get_sessions_for_group(group_id)


@mcp.resource("agents://{agent_id}/sessions")
async def mcp_get_agent_sessions(agent_id: str) -> AllSessionsResponse:
    """检索特定代理的所有会话的 MCP 资源。

    返回:
        包含该代理会话列表的 AllSessionsResponse。
    """
    return await get_sessions_for_agent(agent_id)


# === 路由处理器 ===
@app.post("/v1/memories")
async def add_memory(
    episode: NewEpisode,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
):
    """将记忆事件添加到情景记忆和档案记忆。

    此端点首先根据会话上下文（组、代理、用户、会话 ID）检索适当的情景记忆实例。
    然后将事件添加到情景记忆。如果成功，它还会将消息传递给档案记忆进行摄取。

    参数:
        episode: 包含记忆详情的 NewEpisode 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。

    抛出:
        HTTPException: 如果未找到匹配的情景记忆实例，则返回 404。
        HTTPException: 如果 producer 或 produced_for ID 对给定上下文无效，则返回 400。
    """
    episode.merge_and_validate_session(session)
    episode.update_response_session_header(response)
    await _add_memory(episode)


async def _add_memory(episode: NewEpisode):
    """将记忆事件添加到情景记忆和档案记忆。
    内部函数。由 REST API 和 MCP API 共享。

    有关详细信息，请参阅 add_memory() 的文档字符串。"""
    session = episode.get_session()
    group_id = session.group_id
    inst: EpisodicMemory | None = await cast(
        EpisodicMemoryManager, episodic_memory
    ).get_episodic_memory_instance(
        group_id=group_id if group_id is not None else "",
        agent_id=session.agent_id,
        user_id=session.user_id,
        session_id=session.session_id,
    )
    if inst is None:
        raise episode.new_404_not_found_error("unable to find episodic memory")
    async with AsyncEpisodicMemory(inst) as inst:
        success = await inst.add_memory_episode(
            producer=episode.producer,
            produced_for=episode.produced_for,
            episode_content=episode.episode_content,
            episode_type=episode.episode_type,
            content_type=ContentType.STRING,
            metadata=episode.metadata,
        )
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"""either {episode.producer} or {episode.produced_for}
                        is not in {session.user_id}
                        or {session.agent_id}""",
            )

        ctx = inst.get_memory_context()
        await cast(ProfileMemory, profile_memory).add_persona_message(
            str(episode.episode_content),
            episode.metadata if episode.metadata is not None else {},
            {
                "group_id": ctx.group_id,
                "session_id": ctx.session_id,
                "producer": episode.producer,
                "produced_for": episode.produced_for,
            },
            user_id=episode.producer,
        )


@app.post("/v1/memories/episodic")
async def add_episodic_memory(
    episode: NewEpisode,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
):
    """仅将记忆事件添加到情景记忆。

    此端点首先根据会话上下文（组、代理、用户、会话 ID）检索适当的情景记忆实例。
    然后将事件添加到情景记忆。

    参数:
        episode: 包含记忆详情的 NewEpisode 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。

    抛出:
        HTTPException: 如果未找到匹配的情景记忆实例，则返回 404。
        HTTPException: 如果 producer 或 produced_for ID 对给定上下文无效，则返回 400。
    """
    episode.merge_and_validate_session(session)
    episode.update_response_session_header(response)
    await _add_episodic_memory(episode)


async def _add_episodic_memory(episode: NewEpisode):
    """将记忆事件添加到情景记忆。
    内部函数。由 REST API 和 MCP API 共享。

    有关详细信息，请参阅 add_episodic_memory() 的文档字符串。
    """
    session = episode.get_session()
    group_id = session.group_id
    inst: EpisodicMemory | None = await cast(
        EpisodicMemoryManager, episodic_memory
    ).get_episodic_memory_instance(
        group_id=group_id if group_id is not None else "",
        agent_id=session.agent_id,
        user_id=session.user_id,
        session_id=session.session_id,
    )
    if inst is None:
        raise episode.new_404_not_found_error("unable to find episodic memory")
    async with AsyncEpisodicMemory(inst) as inst:
        success = await inst.add_memory_episode(
            producer=episode.producer,
            produced_for=episode.produced_for,
            episode_content=episode.episode_content,
            episode_type=episode.episode_type,
            content_type=ContentType.STRING,
            metadata=episode.metadata,
        )
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"""either {episode.producer} or {episode.produced_for}
                        is not in {session.user_id}
                        or {session.agent_id}""",
            )


@app.post("/v1/memories/profile")
async def add_profile_memory(
    episode: NewEpisode,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
):
    """将记忆事件添加到档案记忆。

    此端点将事件添加到档案记忆进行摄取。

    参数:
        episode: 包含记忆详情的 NewEpisode 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。

    抛出:
        HTTPException: 如果发生错误，则返回相应的状态码。
    """
    episode.merge_and_validate_session(session)
    episode.update_response_session_header(response)
    await _add_profile_memory(episode)


async def _add_profile_memory(episode: NewEpisode):
    """将记忆事件添加到档案记忆。
    内部函数。由 REST API 和 MCP API 共享。

    有关详细信息，请参阅 add_profile_memory() 的文档字符串。
    """
    session = episode.get_session()
    group_id = session.group_id

    await cast(ProfileMemory, profile_memory).add_persona_message(
        str(episode.episode_content),
        episode.metadata if episode.metadata is not None else {},
        {
            "group_id": group_id if group_id is not None else "",
            "session_id": session.session_id,
            "producer": episode.producer,
            "produced_for": episode.produced_for,
        },
        user_id=episode.producer,
    )


@app.post("/v1/memories/search")
async def search_memory(
    q: SearchQuery,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
) -> SearchResult:
    """在情景记忆和档案记忆中搜索记忆。

    检索相关的情景记忆实例，然后在情景记忆和档案记忆中执行并发搜索。
    结果合并到单个响应对象中。

    参数:
        q: 包含查询和上下文的 SearchQuery 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。

    返回:
        包含两种记忆类型结果的 SearchResult 对象。

    抛出:
        HTTPException: 如果未找到匹配的情景记忆实例，则返回 404。
    """
    q.merge_and_validate_session(session)
    q.update_response_session_header(response)
    return await _search_memory(q)


async def _search_memory(q: SearchQuery) -> SearchResult:
    """在情景记忆和档案记忆中搜索记忆。
    内部函数。由 REST API 和 MCP API 共享。
    有关详细信息，请参阅 search_memory() 的文档字符串。"""
    session = q.get_session()
    inst: EpisodicMemory | None = await cast(
        EpisodicMemoryManager, episodic_memory
    ).get_episodic_memory_instance(
        group_id=session.group_id,
        agent_id=session.agent_id,
        user_id=session.user_id,
        session_id=session.session_id,
    )
    if inst is None:
        raise q.new_404_not_found_error("unable to find episodic memory")
    async with AsyncEpisodicMemory(inst) as inst:
        ctx = inst.get_memory_context()
        user_id = (
            session.user_id[0]
            if session.user_id is not None and len(session.user_id) > 0
            else ""
        )
        res = await asyncio.gather(
            inst.query_memory(q.query, q.limit, q.filter),
            cast(ProfileMemory, profile_memory).semantic_search(
                q.query,
                q.limit if q.limit is not None else 5,
                isolations={
                    "group_id": ctx.group_id,
                    "session_id": ctx.session_id,
                },
                user_id=user_id,
            ),
        )
        return SearchResult(
            content={"episodic_memory": res[0], "profile_memory": res[1]}
        )


@app.post("/v1/memories/episodic/search")
async def search_episodic_memory(
    q: SearchQuery,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
) -> SearchResult:
    """在情景记忆中搜索记忆。

    参数:
        q: 包含查询和上下文的 SearchQuery 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。

    返回:
        包含情景记忆结果的 SearchResult 对象。

    抛出:
        HTTPException: 如果未找到匹配的情景记忆实例，则返回 404。
    """
    q.merge_and_validate_session(session)
    q.update_response_session_header(response)
    return await _search_episodic_memory(q)


async def _search_episodic_memory(q: SearchQuery) -> SearchResult:
    """在情景记忆中搜索记忆。
    内部函数。由 REST API 和 MCP API 共享。
    有关详细信息，请参阅 search_episodic_memory() 的文档字符串。
    """
    session = q.get_session()
    group_id = session.group_id if session.group_id is not None else ""
    inst: EpisodicMemory | None = await cast(
        EpisodicMemoryManager, episodic_memory
    ).get_episodic_memory_instance(
        group_id=group_id,
        agent_id=session.agent_id,
        user_id=session.user_id,
        session_id=session.session_id,
    )
    if inst is None:
        raise q.new_404_not_found_error("unable to find episodic memory")
    async with AsyncEpisodicMemory(inst) as inst:
        res = await inst.query_memory(q.query, q.limit, q.filter)
        return SearchResult(content={"episodic_memory": res})


@app.post("/v1/memories/profile/search")
async def search_profile_memory(
    q: SearchQuery,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
) -> SearchResult:
    """在档案记忆中搜索记忆。

    参数:
        q: 包含查询和上下文的 SearchQuery 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。

    返回:
        包含档案记忆结果的 SearchResult 对象。

    抛出:
        HTTPException: 如果发生错误，则返回相应的状态码。
    """
    q.merge_and_validate_session(session)
    q.update_response_session_header(response)
    return await _search_profile_memory(q)


async def _search_profile_memory(q: SearchQuery) -> SearchResult:
    """在档案记忆中搜索记忆。
    内部函数。由 REST API 和 MCP API 共享。
    有关详细信息，请参阅 search_profile_memory() 的文档字符串。
    """
    session = q.get_session()
    user_id = session.user_id[0] if session.user_id is not None else ""
    group_id = session.group_id if session.group_id is not None else ""

    res = await cast(ProfileMemory, profile_memory).semantic_search(
        q.query,
        q.limit if q.limit is not None else 5,
        isolations={
            "group_id": group_id,
            "session_id": session.session_id,
        },
        user_id=user_id,
    )
    return SearchResult(content={"profile_memory": res})


@app.delete("/v1/memories")
async def delete_session_data(
    delete_req: DeleteDataRequest,
    response: Response,
    session: SessionData = Depends(_get_session_from_header),  # type: ignore
):
    """
    删除特定会话的数据
    参数:
        delete_req: 包含会话信息的 DeleteDataRequest 对象。
        response: 用于更新头的 HTTP 响应对象。
        session: 从请求头合并的会话数据。
    """
    delete_req.merge_and_validate_session(session)
    delete_req.update_response_session_header(response)
    await _delete_session_data(delete_req)


async def _delete_session_data(delete_req: DeleteDataRequest):
    """删除特定会话的所有数据。
    内部函数。由 REST API 和 MCP API 共享。
    有关详细信息，请参阅 delete_session_data() 的文档字符串。
    """
    session = delete_req.get_session()
    inst: EpisodicMemory | None = await cast(
        EpisodicMemoryManager, episodic_memory
    ).get_episodic_memory_instance(
        group_id=session.group_id,
        agent_id=session.agent_id,
        user_id=session.user_id,
        session_id=session.session_id,
    )
    if inst is None:
        raise delete_req.new_404_not_found_error("unable to find episodic memory")
    async with AsyncEpisodicMemory(inst) as inst:
        await inst.delete_data()


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/sessions")
async def get_all_sessions() -> AllSessionsResponse:
    """
    获取所有会话
    """
    sessions = cast(EpisodicMemoryManager, episodic_memory).get_all_sessions()
    return AllSessionsResponse(
        sessions=[
            MemorySession(
                group_id=s.group_id,
                session_id=s.session_id,
                user_ids=s.user_ids,
                agent_ids=s.agent_ids,
            )
            for s in sessions
        ]
    )


@app.get("/v1/users/{user_id}/sessions")
async def get_sessions_for_user(user_id: str) -> AllSessionsResponse:
    """
    获取特定用户的所有会话
    """
    sessions = cast(EpisodicMemoryManager, episodic_memory).get_user_sessions(user_id)
    return AllSessionsResponse(
        sessions=[
            MemorySession(
                group_id=s.group_id,
                session_id=s.session_id,
                user_ids=s.user_ids,
                agent_ids=s.agent_ids,
            )
            for s in sessions
        ]
    )


@app.get("/v1/groups/{group_id}/sessions")
async def get_sessions_for_group(group_id: str) -> AllSessionsResponse:
    """
    获取特定组的所有会话
    """
    sessions = cast(EpisodicMemoryManager, episodic_memory).get_group_sessions(group_id)
    return AllSessionsResponse(
        sessions=[
            MemorySession(
                group_id=s.group_id,
                session_id=s.session_id,
                user_ids=s.user_ids,
                agent_ids=s.agent_ids,
            )
            for s in sessions
        ]
    )


@app.get("/v1/agents/{agent_id}/sessions")
async def get_sessions_for_agent(agent_id: str) -> AllSessionsResponse:
    """
    获取特定代理的所有会话
    """
    sessions = cast(EpisodicMemoryManager, episodic_memory).get_agent_sessions(agent_id)
    return AllSessionsResponse(
        sessions=[
            MemorySession(
                group_id=s.group_id,
                session_id=s.session_id,
                user_ids=s.user_ids,
                agent_ids=s.agent_ids,
            )
            for s in sessions
        ]
    )


# === 健康检查端点 ===
@app.get("/health")
async def health_check():
    """用于容器编排的健康检查端点。"""
    try:
        # 检查内存管理器是否已初始化
        if profile_memory is None or episodic_memory is None:
            raise HTTPException(
                status_code=503, detail="Memory managers not initialized"
            )

        # 基本健康检查 - 可以扩展以检查数据库连接
        return {
            "status": "healthy",
            "service": "memmachine",
            "version": "1.0.0",
            "memory_managers": {
                "profile_memory": profile_memory is not None,
                "episodic_memory": episodic_memory is not None,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


async def start():
    """使用 uvicorn 服务器运行 FastAPI 应用程序。"""
    port_num = os.getenv("PORT", "8080")
    host_name = os.getenv("HOST", "0.0.0.0")

    await uvicorn.Server(
        uvicorn.Config(app, host=host_name, port=int(port_num))
    ).serve()


def main():
    """应用程序的主入口点。"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "%(levelname)-7s %(message)s")
    logging.basicConfig(
        level=log_level,
        format=log_format,
    )
    # 从 .env 文件加载环境变量
    load_dotenv()

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="MemMachine server")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run in MCP stdio mode",
    )
    args = parser.parse_args()

    if args.stdio:
        # MCP stdio 模式
        config_file = os.getenv("MEMORY_CONFIG", "configuration.yml")

        async def run_mcp_server():
            """初始化资源并在同一事件循环中运行 MCP 服务器。"""
            global episodic_memory, profile_memory
            try:
                episodic_memory, profile_memory = await initialize_resource(config_file)
                await profile_memory.startup()
                await mcp.run_stdio_async()
            finally:
                # 服务器停止时清理资源
                if profile_memory:
                    await profile_memory.cleanup()

        asyncio.run(run_mcp_server())
    else:
        # REST API 的 HTTP 模式
        asyncio.run(start())


if __name__ == "__main__":
    main()
