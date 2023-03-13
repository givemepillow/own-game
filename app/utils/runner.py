import asyncio
from asyncio import Task, Future, CancelledError
from logging import getLogger
from typing import Optional, Callable, Awaitable


class Runner:
    """
     Создаёт бесконечный цикл, который на каждой итерации вызывает переданный
     при инициализации хук - асинхронную функцию.
    """

    def __init__(self, hook: Callable[[], Awaitable]):
        self._hook = hook
        self._is_running = False
        self._task: Optional[Task] = None
        self._logger = getLogger("poller")

    async def start(self):
        self._is_running = True
        self._task = asyncio.create_task(self.run())
        self._task.add_done_callback(self._done_callback)

    async def stop(self):
        self._is_running = False
        await asyncio.wait_for(self._task, timeout=3)

    async def run(self):
        try:
            while self._is_running:
                await self._hook()
        except CancelledError:
            self._logger.warning("task cancelled")

    def _done_callback(self, future: Future):
        if future.exception():
            self._logger.exception('running failed', exc_info=future.exception())
