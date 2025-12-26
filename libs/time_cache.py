# timed_cache.py
# ------------------------------------------
# Copyright (c) 2025 1Danish-00
#
# This code is provided under the MIT License.
# You are free to use, modify, and distribute this code with attribution.
#
# Author: 1Danish-00
# GitHub: https://github.com/1Danish-00
# ------------------------------------------

import asyncio
import functools
import inspect
import time
from typing import Any, Callable, Dict, Tuple


def timed_cache(
    seconds: int, max_concurrent: int = None, ignore_args: list[str] = None
):
    """
    A decorator that caches the result of a function for a specified duration (`seconds`),
    avoiding redundant calls with the same arguments. Supports both sync and async functions,
    with advanced handling for concurrent async calls.
    Features:
    - Caches function results based on arguments for `seconds` seconds.
    - Ignores specified arguments (e.g., sessions or connections) in the cache key using `ignore_args`.
    - Deduplicates in-flight async calls: concurrent calls with the same key await the same result.
    - Enforces concurrency limits for async functions using `max_concurrent`.
    Args:
        seconds (int): Duration in seconds to cache the result of each unique call.
        max_concurrent (int, optional): Maximum number of concurrent executions for async functions.
                                        If set, a semaphore is used to limit concurrency.
                                        Only applicable for async functions.
        ignore_args (list[str], optional): List of argument names to exclude from cache key generation.
                                           Useful for excluding non-essential or unhashable types
                                           (e.g., `aiohttp.ClientSession`).
    Returns:
        Callable: A decorated function that caches and manages concurrent executions.
    Raises:
        TypeError: If `max_concurrent` is provided for a synchronous function.
    Example:
        >>> @timed_cache(seconds=100, max_concurrent=10, ignore_args=['session'])
        ... async def fetch_data(session: aiohttp.ClientSession, token):
        ...     async with session.get(url) as response:
        ...         data = await response.json()
        ...         return data
    Notes:
        - Cache keys are created from function arguments excluding those in `ignore_args`.
        - For async functions, if a call is already running with the same key, other calls will wait.
        - For sync functions, concurrent deduplication is not safe and uses a basic in-flight check.
    """

    result_cache: Dict[Tuple, Tuple[float, Any]] = {}
    in_flight_tasks: Dict[Tuple, asyncio.Future] = {}
    semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None
    ignore_args = set(ignore_args or [])

    def decorator(func: Callable):
        is_coroutine = inspect.iscoroutinefunction(func)
        sig = inspect.signature(func)

        if is_coroutine:

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                key_items = tuple(
                    (k, v)
                    for k, v in bound_args.arguments.items()
                    if k not in ignore_args
                )
                key = tuple(sorted(key_items))

                now = time.time()

                # Return from cache if valid
                if key in result_cache:
                    expires_at, value = result_cache[key]
                    if now < expires_at:
                        return value

                # Return in-flight result if already running
                if key in in_flight_tasks:
                    return await in_flight_tasks[key]

                # Create a new future for this key
                future = asyncio.Future()
                in_flight_tasks[key] = future

                # Wait for slot if concurrency limit is set
                if semaphore:
                    async with semaphore:
                        try:
                            result = await func(*args, **kwargs)
                            result_cache[key] = (time.time() + seconds, result)
                            future.set_result(result)
                            return result
                        except Exception as e:
                            future.set_exception(e)
                            raise
                        finally:
                            in_flight_tasks.pop(key, None)
                else:
                    try:
                        result = await func(*args, **kwargs)
                        result_cache[key] = (time.time() + seconds, result)
                        future.set_result(result)
                        return result
                    except Exception as e:
                        future.set_exception(e)
                        raise
                    finally:
                        in_flight_tasks.pop(key, None)

            return async_wrapper

        elif max_concurrent:
            raise TypeError(
                "max_concurrent support only available for async functions."
            )

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                key_items = tuple(
                    (k, v)
                    for k, v in bound_args.arguments.items()
                    if k not in ignore_args
                )
                key = tuple(sorted(key_items))

                now = time.time()

                if key in result_cache:
                    expires_at, value = result_cache[key]
                    if now < expires_at:
                        return value

                # If another call is running, wait for it (not supported in sync safely)
                if key in in_flight_tasks:
                    return in_flight_tasks[key]

                try:
                    in_flight_tasks[key] = result = func(*args, **kwargs)
                    result_cache[key] = (time.time() + seconds, result)
                    return result
                finally:
                    in_flight_tasks.pop(key, None)

            return sync_wrapper

    return decorator
