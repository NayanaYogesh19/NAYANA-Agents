"""
Shared thread pool for blocking OpenRouter HTTP calls.

Single pool used by every router that fires LLM requests (commentary,
ai_analyze) so total concurrent outbound calls stay bounded regardless of
how many endpoints are hit at once — important on resource-constrained
hosts shared with other services.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4)


async def run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(LLM_EXECUTOR, fn, *args)
