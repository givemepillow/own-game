import asyncio
from asyncio import Future
from typing import Type

from app.abc.cleanup_ctx import CleanupCTX
from app.abc.handler import Handler
from app.abc.message import Message
from app.bot.enums import Origin
from app.utils.runner import Runner


class MessageBus(CleanupCTX):
    """
    Шина сообщений - событийно-ориентированный подход.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = asyncio.Queue()
        self._handlers = {}
        self._runner: Runner | None = None
        self._delayed_messages = {}

    async def on_startup(self):
        self._runner = Runner(self.handle)
        await self._runner.start()

    async def on_shutdown(self):
        await self._runner.stop()

    def register(self, handlers: dict[Type[Message], list[Type[Handler]]]):
        """
        Регистрация обработчиков команд и событий.
        :param handlers: словарь, где ключ - событие, а значение список его обработчкиов.
        """
        for message_class, handler_classes in handlers.items():
            self._handlers.setdefault(
                message_class, []
            ).extend([h(self.app) for h in handler_classes])

    async def handle(self):
        message = await self._queue.get()
        for handler in self._handlers.get(type(message), []):
            task = asyncio.create_task(handler(message))
            task.add_done_callback(self._done_callback)
        self._queue.task_done()

    def publish(self, message: Message):
        """
        Публикация команды или события в шину.
        :param message: команда или событие.
        """
        self._queue.put_nowait(message)

    async def postpone(self, message: Message, origin: Origin, chat_id: int, *, delay: int):
        """
        Откладывает ПУБЛИКАЦИЮ события или команды в шину сообщений.
        :param message: события или команда.
        :param origin: источник - необходимо для идентификации событий и команд.
        :param chat_id: - необходимо для идентификации событий и команд.
        :param delay: задержка в секундах (на сколько откладываем.)
        """

        async def _postpone_task():
            await asyncio.sleep(delay)

            self.app.bus.publish(message)

        task = asyncio.create_task(_postpone_task())
        task.add_done_callback(self._done_callback)
        self._delayed_messages[self._hash(message.__class__, origin, chat_id)] = task

    async def cancel(self, message_class: Type[Message], origin: Origin, chat_id: int):
        """
        Отменяет ранее отложенную команд ил сообщение.
        :param message_class: для получения имени класса (команды или события).
        :param origin: - необходимо для идентификации событий и команд.
        :param chat_id: - необходимо для идентификации событий и команд.
        """
        hash_ = self._hash(message_class, origin, chat_id)
        if hash_ in self._delayed_messages:
            self._delayed_messages[hash_].cancel()
            del self._delayed_messages[hash_]

    @staticmethod
    def _hash(message_type: Type[Message], origin: Origin, chat_id: int):
        return hash((message_type, origin, chat_id))

    def _done_callback(self, future: Future):
        if future.exception():
            self.logger.exception('running failed', exc_info=future.exception())
