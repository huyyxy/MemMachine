"""Profile Memory 引擎的核心模块。

本模块包含 `ProfileMemory` 类，这是基于用户对话历史创建、管理和搜索用户档案的核心组件。
它集成了语言模型用于智能信息提取，以及向量数据库用于语义搜索功能。
"""

import asyncio
import datetime
import json
import logging
from itertools import accumulate, groupby, tee
from typing import Any

import numpy as np
from pydantic import BaseModel

from memmachine.common.data_types import ExternalServiceAPIError
from memmachine.common.embedder.embedder import Embedder
from memmachine.common.language_model.language_model import LanguageModel

from .prompt_provider import ProfilePrompt
from .storage.storage_base import ProfileStorageBase
from .util.lru_cache import LRUCache

logger = logging.getLogger(__name__)


class ProfileUpdateTracker:
    """跟踪用户的档案更新活动。
    当用户发送消息时，此类跟踪已发送的消息数量以及第一条消息的发送时间。
    这用于根据消息数量和时间间隔确定何时触发档案更新。
    """

    def __init__(self, user: str, message_limit: int, time_limit_sec: float):
        self._user = user
        self._message_limit: int = message_limit
        self._time_limit: float = time_limit_sec
        self._message_count: int = 0
        self._first_updated: datetime.datetime | None = None

    def mark_update(self):
        """标记用户已发送新消息。
        增加消息计数，如果这是第一条消息，则设置首次更新时间。
        """
        self._message_count += 1
        if self._first_updated is None:
            self._first_updated = datetime.datetime.now()

    def _seconds_from_first_update(self) -> float | None:
        """返回自第一条消息发送以来经过的秒数。
        如果尚未发送任何消息，返回 None。
        """
        if self._first_updated is None:
            return None
        delta = datetime.datetime.now() - self._first_updated
        return delta.total_seconds()

    def reset(self):
        """重置跟踪器状态。
        清除消息计数和首次更新时间。
        """
        self._message_count = 0
        self._first_updated = None

    def should_update(self) -> bool:
        """判断是否应该触发档案更新。
        如果消息数量超过限制，或者自第一条消息以来的时间超过时间限制，
        则会触发档案更新。

        返回:
            bool: 如果应该触发档案更新则返回 True，否则返回 False。
        """
        if self._message_count == 0:
            return False
        elapsed = self._seconds_from_first_update()
        exceed_time_limit = elapsed is not None and elapsed >= self._time_limit
        exceed_msg_limit = self._message_count >= self._message_limit
        return exceed_time_limit or exceed_msg_limit


class ProfileUpdateTrackerManager:
    """管理多个用户的 ProfileUpdateTracker 实例。"""

    def __init__(self, message_limit: int, time_limit_sec: float):
        self._trackers: dict[str, ProfileUpdateTracker] = {}
        self._trackers_lock = asyncio.Lock()
        self._message_limit = message_limit
        self._time_limit_sec = time_limit_sec

    def _new_tracker(self, user: str) -> ProfileUpdateTracker:
        return ProfileUpdateTracker(
            user=user,
            message_limit=self._message_limit,
            time_limit_sec=self._time_limit_sec,
        )

    async def mark_update(self, user: str):
        """标记用户已发送新消息。
        如果该用户不存在跟踪器，则创建一个新的跟踪器。
        """
        async with self._trackers_lock:
            if user not in self._trackers:
                self._trackers[user] = self._new_tracker(user)
            self._trackers[user].mark_update()

    async def get_users_to_update(self) -> list[str]:
        """返回需要更新档案的用户列表。
        如果用户的跟踪器指示应该触发更新，则需要更新档案。
        """
        async with self._trackers_lock:
            ret = []
            for user, tracker in self._trackers.items():
                if tracker.should_update():
                    ret.append(user)
                    tracker.reset()
            return ret


class ProfileMemory:
    # pylint: disable=too-many-instance-attributes
    """基于对话历史管理和维护用户档案。

    此类使用语言模型智能地从对话中提取、更新和整合用户档案信息。
    它将结构化的档案数据（特征、值、标签）及其向量嵌入存储在持久数据库中，
    以实现高效的语义搜索。

    主要功能包括：
    - 摄取对话消息以更新档案。
    - 整合和去重档案条目，以保持准确性和简洁性。
    - 提供档案数据的 CRUD 操作。
    - 对用户档案执行语义搜索。
    - 缓存经常访问的档案以提高性能。

    该过程主要是异步的，设计用于在异步应用程序中工作。

    参数:
        model (LanguageModel): 用于档案提取的语言模型。
        embeddings (Embedder): 用于生成向量嵌入的模型。
        profile_storage (ProfileStorageBase): 与档案数据库的连接。
        prompt (ProfilePrompt): 要使用的系统提示。
        max_cache_size (int, optional): 档案 LRU 缓存的最大大小。
            默认为 1000。
    """

    PROFILE_UPDATE_INTERVAL_SEC = 2
    """ 档案更新的间隔（秒）。这控制后台任务检查需要更新的用户
    并处理其对话历史以更新档案的频率。
    """

    PROFILE_UPDATE_MESSAGE_LIMIT = 5
    """ 触发档案更新的消息数量。
    如果用户发送了这么多消息，将更新其档案。
    """

    PROFILE_UPDATE_TIME_LIMIT_SEC = 120.0
    """ 触发档案更新的时间（秒）。
    如果用户已发送消息，且自第一条消息以来已过去这么长时间，
    将更新其档案。
    """

    def __init__(
        self,
        *,
        model: LanguageModel,
        embeddings: Embedder,
        prompt: ProfilePrompt,
        max_cache_size=1000,
        profile_storage: ProfileStorageBase,
    ):
        if model is None:
            raise ValueError("model must be provided")
        if embeddings is None:
            raise ValueError("embeddings must be provided")
        if prompt is None:
            raise ValueError("prompt must be provided")
        if profile_storage is None:
            raise ValueError("profile_storage must be provided")

        self._model = model
        self._embeddings = embeddings
        self._profile_storage = profile_storage

        self._max_cache_size = max_cache_size

        self._update_prompt = prompt.update_prompt
        self._consolidation_prompt = prompt.consolidation_prompt

        self._update_interval = 1
        self._dirty_users: ProfileUpdateTrackerManager = ProfileUpdateTrackerManager(
            message_limit=self.PROFILE_UPDATE_MESSAGE_LIMIT,
            time_limit_sec=self.PROFILE_UPDATE_TIME_LIMIT_SEC,
        )
        self._ingestion_task = asyncio.create_task(self._background_ingestion_task())
        self._is_shutting_down = False
        self._profile_cache = LRUCache(self._max_cache_size)

    async def startup(self):
        """初始化资源，例如数据库连接池。"""
        await self._profile_storage.startup()

    async def cleanup(self):
        """释放资源，例如数据库连接池。"""
        self._is_shutting_down = True
        await self._ingestion_task
        await self._profile_storage.cleanup()

    # === CRUD ===

    async def get_user_profile(
        self,
        user_id: str,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        """检索用户的档案，使用缓存以提高性能。

        参数:
            user_id: 用户的 ID。
            isolations: 用于数据隔离的字典。

        返回:
            用户的档案数据。
        """
        if isolations is None:
            isolations = {}
        profile = self._profile_cache.get((user_id, json.dumps(isolations)))
        if profile is not None:
            return profile
        profile = await self._profile_storage.get_profile(user_id, isolations)
        self._profile_cache.put((user_id, json.dumps(isolations)), profile)
        return profile

    async def delete_all(self):
        """从数据库中删除所有用户档案并清除缓存。"""
        self._profile_cache = LRUCache(self._max_cache_size)
        await self._profile_storage.delete_all()

    async def delete_user_profile(
        self,
        user_id: str,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        """删除特定用户的档案。

        参数:
            user_id: 要删除其档案的用户 ID。
            isolations: 用于数据隔离的字典。
        """
        if isolations is None:
            isolations = {}
        self._profile_cache.erase((user_id, json.dumps(isolations)))
        await self._profile_storage.delete_profile(user_id, isolations)

    async def add_new_profile(
        self,
        user_id: str,
        feature: str,
        value: str,
        tag: str,
        metadata: dict[str, str] | None = None,
        isolations: dict[str, bool | int | float | str] | None = None,
        citations: list[int] | None = None,
    ):
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
        """向用户档案添加新特征。

        这将使该用户档案的缓存失效。

        参数:
            user_id: 用户的 ID。
            feature: 档案特征（例如，"likes"）。
            value: 特征的值（例如，"dogs"）。
            tag: 特征的类别或标签。
            metadata: 档案条目的附加元数据。
            isolations: 用于数据隔离的字典。
            citations: 作为此特征来源的消息 ID 列表。
        """
        if isolations is None:
            isolations = {}
        if metadata is None:
            metadata = {}
        if citations is None:
            citations = []
        self._profile_cache.erase((user_id, json.dumps(isolations)))
        emb = (await self._embeddings.ingest_embed([value]))[0]
        await self._profile_storage.add_profile_feature(
            user_id,
            feature,
            value,
            tag,
            np.array(emb),
            metadata=metadata,
            isolations=isolations,
            citations=citations,
        )

    async def delete_user_profile_feature(
        self,
        user_id: str,
        feature: str,
        tag: str,
        value: str | None = None,
        isolations: dict[str, bool | int | float | str] | None = None,
    ):
        """从用户档案中删除特定特征。

        这将使该用户档案的缓存失效。

        参数:
            user_id: 用户的 ID。
            feature: 要删除的档案特征。
            tag: 要删除的特征标签。
            value: 要删除的特定值。如果为 None，则删除该特征和标签的所有值。
            isolations: 用于数据隔离的字典。
        """
        if isolations is None:
            isolations = {}
        self._profile_cache.erase((user_id, json.dumps(isolations)))
        await self._profile_storage.delete_profile_feature(
            user_id, feature, tag, value, isolations
        )

    def range_filter(
        self, arr: list[tuple[float, Any]], max_range: float, max_std: float
    ) -> list[Any]:
        """
        基于相似度过滤语义搜索条目列表。

        找到由 semantic_search 返回的条目列表的最长前缀，使得：
         - 最大和最小相似度之间的差值最多为 `max_range`。
         - 相似度分数的标准差最多为 `max_std`。

        参数:
            arr: 元组列表，其中每个元组包含相似度分数和相应的条目。
            max_range: 最高和最低相似度分数之间允许的最大范围。
            max_std: 相似度分数允许的最大标准差。

        返回:
            过滤后的条目列表。
        """
        if len(arr) == 0:
            return []
        new_min = arr[0][0] - max_range
        k, v = zip(*arr)
        k1, k2, _, k4 = tee(k, 4)
        sums = accumulate(k1)
        square_sums = accumulate(i * i for i in k2)
        divs = range(1, len(arr) + 1)
        take = max(
            (d if ((sq - s * s / d) / d) ** 0.5 < max_std else -1)
            for (s, sq, d) in zip(sums, square_sums, divs)
        )
        return [val for (f, val, _) in zip(k4, v, range(take)) if f > new_min]

    async def semantic_search(
        self,
        query: str,
        k: int = 1_000_000,
        min_cos: float = -1.0,
        max_range: float = 2.0,
        max_std: float = 1.0,
        isolations: dict[str, bool | int | float | str] | None = None,
        user_id: str = "",
    ) -> list[Any]:
        """对用户档案执行语义搜索。

        参数:
            user_id: 用户的 ID。
            query: 搜索查询字符串。
            k: 从数据库检索的最大结果数。
            min_cos: 结果的最小余弦相似度。
            max_range: `range_filter` 的最大范围。
            max_std: `range_filter` 的最大标准差。
            isolations: 用于数据隔离的字典。

        返回:
            匹配的档案条目列表，按相似度分数过滤。
        """
        # TODO: 缓存此查询 # pylint: disable=fixme
        if isolations is None:
            isolations = {}
        qemb = (await self._embeddings.search_embed([query]))[0]
        candidates = await self._profile_storage.semantic_search(
            user_id, np.array(qemb), k, min_cos, isolations
        )
        formatted = [(i["metadata"]["similarity_score"], i) for i in candidates]
        return self.range_filter(formatted, max_range, max_std)

    async def get_large_profile_sections(
        self,
        user_id: str,
        thresh: int = 5,
        isolations: dict[str, bool | int | float | str] | None = None,
    ) -> list[list[dict[str, Any]]]:
        """检索包含大量条目的档案部分。

        "部分"是具有相同特征和标签的档案条目组。这用于查找可能需要整合的部分。

        参数:
            user_id: 用户的 ID。
            thresh: 一个部分被视为"大"的最小条目数。
            isolations: 用于数据隔离的字典。

        返回:
            大型档案部分的列表，其中每个部分是档案条目列表。
        """
        # TODO: 无用的包装器。删除？ # pylint: disable=fixme
        if isolations is None:
            isolations = {}
        return await self._profile_storage.get_large_profile_sections(
            user_id, thresh, isolations
        )

    # === Profile Ingestion ===
    async def add_persona_message(
        self,
        content: str,
        metadata: dict[str, str] | None = None,
        isolations: dict[str, bool | int | float | str] | None = None,
        user_id: str = "",  # TODO 完全废弃 user_id 参数
    ):
        """向历史记录添加消息，并可能触发档案更新。

        在达到一定数量的消息（`_update_interval`）后，此方法将触发档案更新和整合过程。

        参数:
            user_id: 用户的 ID。
            content: 消息的内容。
            metadata: 与消息关联的元数据，例如发言者。
            isolations: 用于数据隔离的字典。

        返回:
            一个布尔值，指示是否等待了整合过程。
        """
        # TODO: 添加或采用用于更通用消息修改的系统
        # pylint: disable=fixme
        if metadata is None:
            metadata = {}
        if isolations is None:
            isolations = {}

        if "speaker" in metadata:
            content = f"{metadata['speaker']} sends '{content}'"

        await self._profile_storage.add_history(user_id, content, metadata, isolations)

        await self._dirty_users.mark_update(user_id)

    async def uningested_message_count(self):
        return await self._profile_storage.get_uningested_history_messages_count()

    async def _background_ingestion_task(self):
        while not self._is_shutting_down:
            dirty_users = await self._dirty_users.get_users_to_update()
            logger.debug(
                "ProfileMemory - 后台任务检查需要更新的用户: %s",
                dirty_users,
            )

            if len(dirty_users) == 0:
                await asyncio.sleep(self.PROFILE_UPDATE_INTERVAL_SEC)
                continue

            logger.debug(
                "ProfileMemory - 处理用户的未摄取记忆: %s",
                dirty_users,
            )
            await asyncio.gather(
                *[self._process_uningested_memories(user_id) for user_id in dirty_users]
            )

    async def _get_isolation_grouped_memories(self, user_id: str):
        rows = await self._profile_storage.get_history_messages_by_ingestion_status(
            user_id=user_id,
            k=100,
            is_ingested=False,
        )

        def key_fn(r):
            # 将 JSONB 字典标准化为稳定的字符串键
            return json.dumps(r["isolations"], sort_keys=True)

        rows = sorted(rows, key=key_fn)
        return [list(group) for _, group in groupby(rows, key_fn)]

    async def _process_uningested_memories(
        self,
        user_id: str,
    ):
        logger.debug(
            "ProfileMemory - 处理用户未摄取的记忆: %s", user_id
        )
        message_isolation_groups = await self._get_isolation_grouped_memories(user_id)
        logger.debug(
            "ProfileMemory - 为用户 %s 找到 %d 个消息隔离组",
            len(message_isolation_groups),
            user_id,
        )

        async def process_messages(messages):
            if len(messages) == 0:
                logger.debug("ProfileMemory - 没有要处理的消息")
                return

            logger.debug("ProfileMemory - 处理 %d 条消息", len(messages))
            mark_tasks = []

            for i in range(0, len(messages) - 1):
                message = messages[i]
                logger.debug(
                    "ProfileMemory - 为用户 %s 处理第 %d 条消息", i, user_id
                )
                await self._update_user_profile_think(message)
                mark_tasks.append(
                    self._profile_storage.mark_messages_ingested([message["id"]])
                )

            logger.debug(
                "ProfileMemory - 为用户 %s 处理最后一条消息（带整合）",
                user_id,
            )
            await self._update_user_profile_think(messages[-1], wait_consolidate=True)
            mark_tasks.append(
                self._profile_storage.mark_messages_ingested([messages[-1]["id"]])
            )
            await asyncio.gather(*mark_tasks)

        tasks = []
        for isolation_messages in message_isolation_groups:
            tasks.append(process_messages(isolation_messages))

        await asyncio.gather(*tasks)

    async def _update_user_profile_think(
        self,
        record: Any,
        wait_consolidate: bool = False,
    ):
        """
        在执行思维链后，基于 JSON 输出更新用户档案。
        """
        # TODO: 这些真的不应该是原始数据结构。
        citation_id = record["id"]  # 认为这是一个整数
        user_id = record["user_id"]
        isolations = json.loads(record["isolations"])
        # metadata = json.loads(record["metadata"])

        profile = await self.get_user_profile(user_id, isolations)
        memory_content = record["content"]

        user_prompt = (
            "The old profile is provided below:\n"
            "<OLD_PROFILE>\n"
            "{profile}\n"
            "</OLD_PROFILE>\n"
            "\n"
            "The history is provided below:\n"
            "<HISTORY>\n"
            "{memory_content}\n"
            "</HISTORY>\n"
        ).format(
            profile=str(profile),
            memory_content=memory_content,
        )
        # 使用思维链获取实体档案更新命令。
        logger.debug(
            "ProfileMemory - 调用 LLM 更新档案，user_id: %s", user_id
        )
        try:
            response_text, _ = await self._model.generate_response(
                system_prompt=self._update_prompt, user_prompt=user_prompt
            )
            logger.debug(
                "ProfileMemory - 收到 LLM 响应，user_id: %s", user_id
            )
            logger.debug(
                "ProfileMemory - 原始 LLM 响应，user_id %s: %s",
                user_id,
                response_text,
            )
        except (ExternalServiceAPIError, ValueError, RuntimeError) as e:
            logger.error("更新档案时出错: %s", str(e))
            return

        # 从语言模型响应中获取思考和 JSON。
        # 尝试多种解析策略以处理不同的响应格式
        thinking = ""
        response_json = ""

        # 策略 1: 查找 <think> 标签
        if "<think>" in response_text and "</think>" in response_text:
            thinking, _, response_json = response_text.removeprefix(
                "<think>"
            ).rpartition("</think>")
            thinking = thinking.strip()
        # 策略 2: 在响应中查找 JSON 对象
        else:
            # 通过查找常见模式尝试从响应中提取 JSON
            import re

            # 查找包装在各种标签中的 JSON 对象
            json_patterns = [
                r"<OLD_PROFILE>\s*(\{.*?\})\s*</OLD_PROFILE>",
                r"<NEW_PROFILE>\s*(\{.*?\})\s*</NEW_PROFILE>",
                r"<profile>\s*(\{.*?\})\s*</profile>",
                r"<json>\s*(\{.*?\})\s*</json>",
                r"```json\s*(\{.*?\})\s*```",
                r"```\s*(\{.*?\})\s*```",
                r"<think>\s*(\{.*?\})\s*</think>",
            ]

            response_json = ""
            for pattern in json_patterns:
                match = re.search(pattern, response_text, re.DOTALL)
                if match:
                    response_json = match.group(1).strip()
                    break

            # 如果未找到带标签的 JSON，尝试在响应末尾查找 JSON
            if not response_json:
                # 查找响应中的最后一个 JSON 对象
                json_match = re.search(
                    r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", response_text
                )
                if json_match:
                    response_json = json_match.group(1).strip()
                else:
                    # 如果仍未找到 JSON，使用整个响应
                    response_json = response_text.strip()

        # 清理常见的 JSON 语法问题
        if response_json:
            # 删除无效语法，如 "... (other tags remain the same)"
            response_json = re.sub(r"\.\.\.\s*\([^)]*\)", "", response_json)
            # 删除右大括号前的尾随逗号
            response_json = re.sub(r",(\s*[}\]])", r"\1", response_json)

            # 修复常见的 LLM JSON 格式化问题
            # 修复未加引号的属性名（例如，tag: "value" -> "tag": "value"）
            response_json = re.sub(r"(\w+):\s*", r'"\1": ', response_json)

            # 将单引号修复为双引号
            response_json = re.sub(r"'([^']*)'", r'"\1"', response_json)

            # 将反引号修复为双引号
            response_json = re.sub(r"`([^`]*)`", r'"\1"', response_json)

            # 修复不完整的 JSON 结构（例如，缺少右大括号）
            open_braces = response_json.count("{")
            close_braces = response_json.count("}")
            if open_braces > close_braces:
                response_json += "}" * (open_braces - close_braces)

            # 删除任何剩余的无效字符
            response_json = response_json.strip()

        logger.debug(
            "ProfileMemory - 为用户 %s 提取的 JSON: %s", user_id, response_json
        )

        # TODO: 这些真的不应该是原始数据结构。
        try:
            profile_update_commands = json.loads(response_json)
            logger.debug(
                "ProfileMemory - 成功为用户 %s 解析 JSON: %s",
                user_id,
                profile_update_commands,
            )
        except ValueError as e:
            logger.warning(
                "无法将语言模型输出 '%s' 加载为 JSON，错误 %s。"
                "尝试从格式错误的响应中提取有效的 JSON。",
                str(response_json),
                str(e),
            )

            # 尝试从格式错误的响应中提取有效的 JSON
            try:
                # 尝试查找并提取 JSON 对象
                json_objects = []
                brace_count = 0
                current_json = ""
                in_string = False
                escape_next = False

                for char in response_json:
                    if escape_next:
                        current_json += char
                        escape_next = False
                        continue

                    if char == "\\":
                        escape_next = True
                        current_json += char
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string

                    current_json += char

                    if not in_string:
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0 and current_json.strip():
                                # 找到了一个完整的 JSON 对象
                                try:
                                    obj = json.loads(current_json.strip())
                                    json_objects.append(obj)
                                except (
                                    json.JSONDecodeError,
                                    ValueError,
                                ) as decode_error:
                                    # 忽略格式错误的 JSON 片段；继续扫描
                                    logger.debug(
                                        "提取过程中跳过无效的 JSON 对象: %s",
                                        str(decode_error),
                                    )
                                current_json = ""

                if json_objects:
                    # 将所有有效的 JSON 对象合并为一个
                    combined_json = {}
                    for i, obj in enumerate(json_objects):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                combined_json[f"{i}_{key}"] = value

                    profile_update_commands = combined_json
                    logger.debug(
                        "ProfileMemory - 成功从格式错误的响应中为用户 %s 提取 JSON: %s",
                        user_id,
                        profile_update_commands,
                    )
                else:
                    logger.warning(
                        "无法从格式错误的响应中提取有效的 JSON。继续执行，但没有档案更新命令。"
                    )
                    profile_update_commands = {}
                    return

            except Exception as extraction_error:
                logger.warning(
                    "从格式错误的响应中提取 JSON 失败。错误: %s。"
                    "继续执行，但没有档案更新命令。",
                    str(extraction_error),
                )
                profile_update_commands = {}
                return
        finally:
            logger.info(
                "PROFILE MEMORY INGESTOR",
                extra={
                    "queries_to_ingest": memory_content,
                    "thoughts": thinking,
                    "outputs": profile_update_commands,
                },
            )

        # 这可能应该只是一个命令列表，
        # 而不是从字符串中的整数（甚至不是裸整数！）到命令的字典映射。
        # TODO: 考虑在破坏性更改中改进此设计。
        if not isinstance(profile_update_commands, dict):
            logger.warning(
                "AI 响应格式不正确: 期望字典，得到 %s %s",
                type(profile_update_commands).__name__,
                profile_update_commands,
            )
            return

        commands = profile_update_commands.values()

        valid_commands = []
        for command in commands:
            if not isinstance(command, dict):
                logger.warning(
                    "AI 响应格式不正确: "
                    "期望档案更新命令为字典，得到 %s %s",
                    type(command).__name__,
                    command,
                )
                continue

            if "command" not in command:
                logger.warning(
                    "AI 响应格式不正确: 缺少 'command' 键: %s",
                    command,
                )
                continue

            if command["command"] not in ("add", "delete"):
                logger.warning(
                    "AI 响应格式不正确: "
                    "期望档案更新命令中的 'command' 值为 'add' 或 'delete'，得到 '%s'",
                    command["command"],
                )
                continue

            if "feature" not in command:
                logger.warning(
                    "AI 响应格式不正确: 缺少 'feature' 键: %s",
                    command,
                )
                continue

            if "tag" not in command:
                logger.warning(
                    "AI 响应格式不正确: 缺少 'tag' 键: %s",
                    command,
                )
                continue

            if command["command"] == "add" and "value" not in command:
                logger.warning(
                    "AI 响应格式不正确: 缺少 'value' 键: %s",
                    command,
                )
                continue

            valid_commands.append(command)

        logger.debug(
            "ProfileMemory - 为用户 %s 执行 %d 个有效命令",
            len(valid_commands),
            user_id,
        )
        for command in valid_commands:
            if command["command"] == "add":
                logger.debug(
                    "ProfileMemory - 为用户 %s 添加档案特征: %s",
                    user_id,
                    command,
                )
                await self.add_new_profile(
                    user_id,
                    command["feature"],
                    command["value"],
                    command["tag"],
                    citations=[citation_id],
                    isolations=isolations,
                    # metadata=metadata
                )
                logger.debug(
                    "ProfileMemory - 成功为用户 %s 添加档案特征",
                    user_id,
                )
            elif command["command"] == "delete":
                value = command["value"] if "value" in command else None
                logger.debug(
                    "ProfileMemory - 为用户 %s 删除档案特征: %s",
                    user_id,
                    command,
                )
                await self.delete_user_profile_feature(
                    user_id,
                    command["feature"],
                    command["tag"],
                    value=value,
                    isolations=isolations,
                )
            else:
                logger.error("未知操作的命令: %s", command["command"])
                raise ValueError(
                    "未知操作的命令: " + str(command["command"])
                )

        if wait_consolidate:
            s = await self.get_large_profile_sections(
                user_id, thresh=5, isolations=isolations
            )
            await asyncio.gather(
                *[self._deduplicate_profile(user_id, section) for section in s]
            )

    async def _deduplicate_profile(
        self,
        user_id: str,
        memories: list[dict[str, Any]],
    ):
        """
        将特征列表发送给 LLM 进行整合。
        """
        try:
            response_text, _ = await self._model.generate_response(
                system_prompt=self._consolidation_prompt,
                user_prompt=json.dumps(memories),
            )
            logger.debug(
                "ProfileMemory - 整合的原始 LLM 响应: %s", response_text
            )
        except (ExternalServiceAPIError, ValueError, RuntimeError) as e:
            logger.error("去重档案时模型错误: %s", str(e))
            return

        # 从语言模型响应中获取思考和 JSON。
        # 尝试多种解析策略以处理不同的响应格式
        thinking = ""
        response_json = ""

        # 策略 1: 查找 <think> 标签
        if "<think>" in response_text and "</think>" in response_text:
            thinking, _, response_json = response_text.removeprefix(
                "<think>"
            ).rpartition("</think>")
            thinking = thinking.strip()
        # 策略 2: 在响应中查找 JSON 对象
        else:
            # 通过查找常见模式尝试从响应中提取 JSON
            import re

            # 查找包装在各种标签中的 JSON 对象
            json_patterns = [
                r"<OLD_PROFILE>\s*(\{.*?\})\s*</OLD_PROFILE>",
                r"<NEW_PROFILE>\s*(\{.*?\})\s*</NEW_PROFILE>",
                r"<profile>\s*(\{.*?\})\s*</profile>",
                r"<json>\s*(\{.*?\})\s*</json>",
                r"```json\s*(\{.*?\})\s*```",
                r"```\s*(\{.*?\})\s*```",
                r"<think>\s*(\{.*?\})\s*</think>",
            ]

            response_json = ""
            for pattern in json_patterns:
                match = re.search(pattern, response_text, re.DOTALL)
                if match:
                    response_json = match.group(1).strip()
                    break

            # 如果未找到带标签的 JSON，尝试在响应末尾查找 JSON
            if not response_json:
                # 查找响应中的最后一个 JSON 对象
                json_match = re.search(
                    r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", response_text
                )
                if json_match:
                    response_json = json_match.group(1).strip()
                else:
                    # 如果仍未找到 JSON，使用整个响应
                    response_json = response_text.strip()

        # 清理常见的 JSON 语法问题
        if response_json:
            # 删除无效语法，如 "... (other tags remain the same)"
            response_json = re.sub(r"\.\.\.\s*\([^)]*\)", "", response_json)
            # 删除右大括号前的尾随逗号
            response_json = re.sub(r",(\s*[}\]])", r"\1", response_json)

            # 修复常见的 LLM JSON 格式化问题
            # 修复未加引号的属性名（例如，tag: "value" -> "tag": "value"）
            response_json = re.sub(r"(\w+):\s*", r'"\1": ', response_json)

            # 将单引号修复为双引号
            response_json = re.sub(r"'([^']*)'", r'"\1"', response_json)

            # 将反引号修复为双引号
            response_json = re.sub(r"`([^`]*)`", r'"\1"', response_json)

            # 修复不完整的 JSON 结构（例如，缺少右大括号）
            open_braces = response_json.count("{")
            close_braces = response_json.count("}")
            if open_braces > close_braces:
                response_json += "}" * (open_braces - close_braces)

            # 删除任何剩余的无效字符
            response_json = response_json.strip()

        logger.debug(
            "ProfileMemory - 整合提取的 JSON: %s", response_json
        )
        try:
            updated_profile_entries = json.loads(response_json)
            logger.debug(
                "ProfileMemory - 成功解析整合的 JSON: %s",
                updated_profile_entries,
            )
        except ValueError as e:
            logger.warning(
                "无法将语言模型输出 '%s' 加载为 JSON，错误 %s",
                str(response_json),
                str(e),
            )
            # 当 JSON 解析失败时记录原始响应以便调试
            logger.debug("解析失败的原始 LLM 响应: %s", response_text)
            updated_profile_entries = {}
            return
        finally:
            logger.info(
                "PROFILE MEMORY CONSOLIDATOR",
                extra={
                    "receives": memories,
                    "thoughts": thinking,
                    "outputs": updated_profile_entries,
                },
            )

        if not isinstance(updated_profile_entries, dict):
            logger.warning(
                "AI 响应格式不正确: 期望字典，得到 %s %s",
                type(updated_profile_entries).__name__,
                updated_profile_entries,
            )
            return

        if "consolidate_memories" not in updated_profile_entries:
            logger.warning(
                "AI 响应格式不正确: "
                "缺少 'consolidate_memories' 键，得到 %s",
                updated_profile_entries,
            )
            updated_profile_entries["consolidate_memories"] = []

        keep_all_memories = False

        if "keep_memories" not in updated_profile_entries:
            logger.warning(
                "AI 响应格式不正确: 缺少 'keep_memories' 键，得到 %s",
                updated_profile_entries,
            )
            updated_profile_entries["keep_memories"] = []
            keep_all_memories = True

        consolidate_memories = updated_profile_entries["consolidate_memories"]
        keep_memories = updated_profile_entries["keep_memories"]

        if not isinstance(consolidate_memories, list):
            logger.warning(
                "AI 响应格式不正确: "
                "'consolidate_memories' 值不是列表，得到 %s %s",
                type(consolidate_memories).__name__,
                consolidate_memories,
            )
            consolidate_memories = []
            keep_all_memories = True

        if not isinstance(keep_memories, list):
            logger.warning(
                "AI 响应格式不正确: "
                "'keep_memories' 值不是列表，得到 %s %s",
                type(keep_memories).__name__,
                keep_memories,
            )
            keep_memories = []
            keep_all_memories = True

        if not keep_all_memories:
            valid_keep_memories = []
            for memory_id in keep_memories:
                if not isinstance(memory_id, int):
                    logger.warning(
                        "AI 响应格式不正确: "
                        "期望 'keep_memories' 中的整数记忆 ID，得到 %s %s",
                        type(memory_id).__name__,
                        memory_id,
                    )
                    continue

                valid_keep_memories.append(memory_id)

            for memory in memories:
                if memory["metadata"]["id"] not in valid_keep_memories:
                    self._profile_cache.erase(user_id)
                    await self._profile_storage.delete_profile_feature_by_id(
                        memory["metadata"]["id"]
                    )

        class ConsolidateMemoryMetadata(BaseModel):
            citations: list[int]

        class ConsolidateMemory(BaseModel):
            tag: str
            feature: str
            value: str
            metadata: ConsolidateMemoryMetadata

        for memory in consolidate_memories:
            try:
                consolidate_memory = ConsolidateMemory(**memory)
            except Exception as e:
                logger.warning(
                    "AI 响应格式不正确: 无法解析记忆 %s，错误 %s",
                    memory,
                    str(e),
                )
                continue

            associations = await self._profile_storage.get_all_citations_for_ids(
                consolidate_memory.metadata.citations
            )

            new_citations = [i[0] for i in associations]

            # 派生项应包含其所有组件的路由信息，这些组件不会相互冲突。
            new_isolations: dict[str, bool | int | float | str] = {}
            bad = set()
            for i in associations:
                for k, v in i[1].items():
                    old_val = new_isolations.get(k)
                    if old_val is None:
                        new_isolations[k] = v
                    elif old_val != v:
                        bad.add(k)
            for k in bad:
                del new_isolations[k]
            logger.debug(
                "CITATION_CHECK",
                extra={
                    "content_citations": new_citations,
                    "profile_citations": consolidate_memory.metadata.citations,
                    "think": thinking,
                },
            )
            await self.add_new_profile(
                user_id,
                consolidate_memory.feature,
                consolidate_memory.value,
                consolidate_memory.tag,
                citations=new_citations,
                isolations=new_isolations,
            )
