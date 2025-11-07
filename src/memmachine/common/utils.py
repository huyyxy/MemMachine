"""
通用工具函数。
"""

import asyncio
import functools
from collections.abc import Awaitable
from contextlib import AbstractAsyncContextManager
from typing import Any


async def async_with(
    async_context_manager: AbstractAsyncContextManager,
    awaitable: Awaitable,
) -> Any:
    """
    使用异步上下文管理器与可等待对象的辅助函数。

    Args:
        async_context_manager (AbstractAsyncContextManager):
            要使用的异步上下文管理器。
        awaitable (Awaitable):
            在上下文中执行的可等待对象。

    Returns:
        Any:
            可等待对象的结果。
    """
    async with async_context_manager:
        return await awaitable


def async_locked(func):
    """
    装饰器，确保协程函数在使用锁的情况下执行。
    该锁在所有被装饰协程函数的调用中共享。
    """
    lock = asyncio.Lock()

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with lock:
            return await func(*args, **kwargs)

    return wrapper
