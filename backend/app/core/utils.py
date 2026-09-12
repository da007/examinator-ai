# app/core/utils.py
import asyncio
import logging

def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    if loop.is_running():
        # В режиме EAGER мы уже в петле. 
        # Нам нужно дождаться результата, не блокируя петлю навсегда.
        # Для Celery Eager это допустимый хак.
        return asyncio.ensure_future(coro)
    return asyncio.run(coro)