import asyncio
from asyncio import Future
from asyncio.exceptions import CancelledError
from typing import Type

from app.abc.cleanup_ctx import CleanupCTX
from app.abc.handler import Handler
from app.abc.message import Message
from app.bot.enums import Origin
from app.game.models import DelayedMessage
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
        await self._restore()
        await self._runner.start()

    async def on_shutdown(self):
        await self._queue.join()
        await self._runner.stop()

    def register(self, handlers: dict[Type[Message], list[Type[Handler]]]):
        """
        Регистрация обработчиков команд и событий.
        :param handlers: словарь, где ключ - событие, а значение список его обработчкиов.
        """
        for message_class, handler_classes in handlers.items():
            self._handlers.setdefault(
                message_class.__name__, []
            ).extend([h(self.app) for h in handler_classes])

    async def handle(self):
        message = await self._queue.get()
        for handler in self._handlers.get(message.__class__.__name__, []):
            task = asyncio.create_task(handler(message))
            task.add_done_callback(self._done_callback)
        self._queue.task_done()

    def publish(self, message: Message):
        """
        Публикация команды или события в шину.
        :param message: команда или событие.
        """
        self._queue.put_nowait(message)

    async def postpone_publish(self, message: Message, origin: Origin, chat_id: int, *, delay: int):
        """
        Откладывает ПУБЛИКАЦИЮ события или команды в шину сообщений.
        :param message: события или команда.
        :param origin: источник - необходимо для идентификации событий и команд.
        :param chat_id: - необходимо для идентификации событий и команд.
        :param delay: задержка в секундах (на сколько откладываем.)
        """
        await self._save(message, origin, chat_id, delay)
        await self._postpone(message, origin, chat_id, delay)

    async def cancel(self, message_class: Type[Message], origin: Origin, chat_id: int):
        """
        Отменяет ранее отложенную команд ил сообщение.
        :param message_class: для получения имени класса (команды или события).
        :param origin: - необходимо для идентификации событий и команд.
        :param chat_id: - необходимо для идентификации событий и команд.
        """

        hash_ = self._hash(message_class, origin, chat_id)
        if hash_ in self._delayed_messages:
            task, _ = self._delayed_messages[hash_]
            task.cancel()
            del self._delayed_messages[hash_]

        async with self.app.store.db() as uow:
            await uow.delayed_messages.delete(message_class.__name__, origin, chat_id)
            await uow.commit()

    async def cancel_all(self, origin: Origin, chat_id: int):
        """
        Отменяет ранее отложенную команд ил сообщение.
        :param origin: - необходимо для идентификации событий и команд.
        :param chat_id: - необходимо для идентификации событий и команд.
        """

        async with self.app.store.db() as uow:
            delayed_messages = await uow.delayed_messages.list(origin, chat_id)
            for dm in delayed_messages:
                message = Message.from_model(dm)
                await self.cancel(message.__class__, dm.origin, dm.chat_id)

    async def force_publish(self, message_class: Type[Message], origin: Origin, chat_id: int):
        """
        Немедленно опубликовать отложенное сообщение.
        :param message_class: для получения имени класса (команды или события).
        :param origin: - необходимо для идентификации событий и команд.
        :param chat_id: - необходимо для идентификации событий и команд.
        """
        hash_ = self._hash(message_class, origin, chat_id)
        if hash_ in self._delayed_messages:
            _, message = self._delayed_messages[hash_]
            await self.cancel(message_class, origin, chat_id)
            self.publish(message)

    async def _postpone(self, message: Message, origin: Origin, chat_id: int, delay: int):
        async def _postpone_task():
            await asyncio.sleep(delay)

            self.app.bus.publish(message)

            async with self.app.store.db() as uow:
                await uow.delayed_messages.delete(message.name, origin, chat_id)
                await uow.commit()

        task = asyncio.create_task(_postpone_task())
        task.add_done_callback(self._done_callback)
        self._delayed_messages[self._hash(message.__class__, origin, chat_id)] = (task, message)

    @staticmethod
    def _hash(message_type: Type[Message], origin: Origin, chat_id: int):
        return hash((message_type.__name__, origin, chat_id))

    def _done_callback(self, future: Future):
        try:
            match future.exception():
                case CancelledError():
                    pass
                case BaseException() as e:
                    self.logger.exception('running failed', exc_info=e)
        except CancelledError:
            pass

    async def _save(self, message: Message, origin: Origin, chat_id: int, delay: int):
        async with self.app.store.db() as uow:
            delayed_message = DelayedMessage(
                origin=origin,
                chat_id=chat_id,
                name=message.name,
                data=bytes(message),
                delay=delay
            )
            uow.delayed_messages.add(delayed_message)
            await uow.commit()

    async def _restore(self):
        self.logger.info("restoring delayed messages...")
        async with self.app.store.db() as uow:
            delayed_messages = await uow.delayed_messages.list()
            for dm in delayed_messages:
                await self._postpone(Message.from_model(dm), dm.origin, dm.chat_id, delay=dm.seconds_remaining)
            await uow.commit()
