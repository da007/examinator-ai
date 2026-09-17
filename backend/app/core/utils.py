import asyncio
import logging

def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    if loop.is_running():
        return asyncio.ensure_future(coro)
    return asyncio.run(coro)