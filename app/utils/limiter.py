from asyncio import Lock
from collections import OrderedDict
from typing import Callable

from aiolimiter import AsyncLimiter


class Limiter:

    def __init__(self, factory: Callable[[], AsyncLimiter | Lock], capacity: int = 30):
        self.cache = OrderedDict()
        self.capacity = capacity
        self._factory = factory

    def __getitem__(self, chat_id: int) -> AsyncLimiter | Lock:
        if chat_id not in self.cache:
            return self._put(chat_id)
        else:
            self.cache.move_to_end(chat_id)
            return self.cache[chat_id]

    def _put(self, chat_id: int) -> AsyncLimiter | Lock:
        self.cache[chat_id] = self._factory()
        self.cache.move_to_end(chat_id)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
        return self.cache[chat_id]
