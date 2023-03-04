from app.abc.bot_view import BotView
from app.bot.enums import ChatType
from app.bot.updates import BotCommand, BotCallbackQuery, BotMessage
from app.bot.markers import command, callback_query, message
from app.game import commands
from app.game.keyboards import CallbackType


@callback_query(chat_type=ChatType.GROUP, data_type='_')
class CallbackPlug(BotView):
    async def handle(self, update: BotCallbackQuery):
        # await self.app.bot(update).callback()
        pass


@command(chat_type=ChatType.GROUP, commands=['play', 'играть', 'start', 'начать'])
class PlayBotCommand(BotView):
    async def handle(self, update: BotCommand):
        self.app.bus.publish(commands.Play(update))


@command(chat_type=ChatType.GROUP, commands=['cancel', 'finish', 'завершить', 'отменить', 'end'])
class FinishBotCommand(BotView):
    async def handle(self, update: BotCommand):
        self.app.bus.publish(commands.CancelGame(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.BECOME_LEADING)
class BecomeLeading(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.SetLeading(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.JOIN)
class GameRegistration(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.Join(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.CANCEL_JOIN)
class GameCancelRegistration(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.CancelJoin(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.START_GAME)
class StartGame(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.StartGame(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.SELECT_QUESTION)
class QuestionSelection(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.SelectQuestion(update, int(update.callback_data.value)))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.PRESS_BUTTON)
class AnswerButtonPress(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.PressButton(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.PEEK)
class PeekAnswer(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.PeekAnswer(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.ACCEPT)
class AcceptAnswer(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.AcceptAnswer(update))


@callback_query(chat_type=ChatType.GROUP, data_type=CallbackType.REJECT)
class RejectAnswer(BotView):
    async def handle(self, update: BotCallbackQuery):
        self.app.bus.publish(commands.RejectAnswer(update))


@message(chat_type=ChatType.GROUP, )
class PlayerAnswer(BotView):
    async def handle(self, update: BotMessage):
        self.app.bus.publish(commands.Answer(update))


VIEWS = [
    CallbackPlug,
    PlayBotCommand,
    GameRegistration,
    GameCancelRegistration,
    StartGame,
    FinishBotCommand,
    AnswerButtonPress,
    QuestionSelection,
    PlayerAnswer,
    PeekAnswer,
    AcceptAnswer,
    RejectAnswer,
    BecomeLeading
]
