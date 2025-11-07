"""
语言模型的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import Any


class LanguageModel(ABC):
    """
    语言模型的抽象基类。
    """

    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, str] | None = None,
        max_attempts: int = 1,
    ) -> tuple[str, Any]:
        """
        根据提供的提示词和工具生成响应。

        Args:
            system_prompt (str | None, optional):
                用于指导模型行为的系统提示词
                (默认: None)。
            user_prompt (str | None, optional):
                包含主要输入的用户提示词
                (默认: None)。
            tools (list[dict[str, Any]] | None, optional):
                模型在响应中可以使用的工具列表（如果支持）
                (默认: None)。
            tool_choice (str | dict[str, str] | None, optional):
                工具选择策略（如果支持）。
                可以是 "auto" 表示自动选择，
                "required" 表示至少使用一个工具，
                或指定特定工具。
                如果为 None，则使用实现定义的默认值
                (默认: None)。
            max_attempts (int, optional):
                在放弃之前尝试的最大次数
                (默认: 1)。

        Returns:
            tuple[str, Any]:
                包含生成的响应文本和工具调用输出（如果有）的元组。

        Raises:
            ExternalServiceAPIError:
                来自底层嵌入 API 的错误。
            ValueError:
                无效输入或 max_attempts。
        """
        raise NotImplementedError
