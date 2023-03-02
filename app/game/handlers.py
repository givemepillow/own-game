from sqlalchemy.exc import IntegrityError

from app.abc.handler import Handler

from app.game import commands, events
from app.game.enums import GameState
from app.game.models import Game, Player
from app.game import keyboards as kb


class GameCreator(Handler):
    async def handler(self, msg: commands.Play):
        try:
            async with self.app.store.db() as uow:
                game = Game(msg.update.origin, msg.update.chat_id)
                uow.games.add(game)
                await uow.commit()
        except IntegrityError as e:
            if e.code == 'gkpj':
                await self.app.bot(msg.update).send("Игра уже начата!")
        else:
            await self.app.bot(msg.update).send(
                "Регистрация началась!", kb.make_registration()
            )


class GameDestroyer(Handler):
    async def handler(self, msg: commands.Play):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            if game:
                game.finish()
                await uow.games.delete(msg.update.origin, msg.update.chat_id)
                await self.app.bot(msg.update).send("Игра досрочно завершена!")
            else:
                await self.app.bot(msg.update).send("Игры и так не было!")
            await uow.commit()


class GameJoin(Handler):
    async def handler(self, msg: commands.Join):
        try:
            async with self.app.store.db() as uow:
                game = await uow.games.get(msg.update.origin, msg.update.chat_id)
                player = Player(msg.update.origin, msg.update.user_id)
                game.players.append(player)
                player_number = len(game.players)
                await uow.commit()

        except IntegrityError as e:
            if e.code == 'gkpj':
                await self.app.bot(msg.update).callback("Вы уже зарегистрированы!")
            else:
                raise
        else:
            await self.app.bot(msg.update).edit(
                "Регистрация началась!",
                inline_keyboard=kb.make_registration(player_number)
            )
            await self.app.bot(msg.update).callback("Вы зарегистрировались в игре!")


class GameCancelJoin(Handler):
    async def handler(self, msg: commands.CancelJoin):
        try:
            async with self.app.store.db() as uow:
                game = await uow.games.get(msg.update.origin, msg.update.chat_id)
                player = Player(msg.update.origin, msg.update.user_id)
                game.players.remove(player)
                player_number = len(game.players)
                await uow.commit()
        except ValueError:
            await self.app.bot(msg.update).callback("Вы и так вне игры!")
        else:
            await self.app.bot(msg.update).edit(
                "Регистрация началась!",
                inline_keyboard=kb.make_registration(player_number)
            )
            await self.app.bot(msg.update).callback("Вы ОТМЕНИЛИ регистрацию в игре!")


class GameStarter(Handler):
    async def handler(self, msg: commands.StartGame):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            themes = await uow.themes.list()
            game.themes.extend(themes)
            player = game.start_game()
            await uow.commit()

            user = await self.app.bot(msg.update).get_user(game.chat_id, player.user_id)
            await self.app.bot(msg.update).edit(
                f"Гадание на кофейной гуще привело к тому, "
                f"что {user.mention} будет первым выбирать вопрос...",
                inline_keyboard=kb.make_table(game.themes, game.selected_questions))


class QuestionSelector(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        async with self.app.store.db() as uow:
            # game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            player = await uow.players.get(msg.update.origin, msg.update.user_id)
            if player and player.is_current:
                question = player.game.select_question(msg.question_id)
                await self.app.bot(msg.update).edit(question.question, inline_keyboard=kb.make_answer_button())
            else:
                await self.app.bot(msg.update).callback("Сейчас не вы выбираете вопрос!")
            await uow.commit()


class FirstPressedPlayer(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        bot = self.app.bot(msg.update)
        async with self.app.store.db() as uow:
            player = await uow.players.get(msg.update.origin, msg.update.user_id)
            if not player:
                return
            # game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            player.game.press_answer_button(player)
            user = await bot.get_user(player.game.game.chat_id, player.user_id)
            await self.app.bot(msg.update).edit(remove_inline_keyboard=True)
            await self.app.bot(msg.update).send(f"{user.mention}, вы всех опередили! Отвечайте.")
            await uow.commit()


class PlayerAnswer(Handler):
    async def handler(self, msg: commands.Answer):
        async with self.app.store.db() as uow:
            player = await uow.players.get(msg.update.origin, msg.update.user_id)
            if player is None or not player.is_answering:
                return
            # game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            if player.game.state != GameState.WAITING_FOR_ANSWER:
                return
            player.game.answer(player)
            await uow.commit()
        await self.app.bot(msg.update).send("Что скажет ведущий?", kb.make_checker())


class PeekAnswer(Handler):
    async def handler(self, msg: commands.PeekAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            await self.app.bot(msg.update).callback(f"{game.current_question.answer}")
            await uow.commit()


class AcceptAnswer(Handler):
    async def handler(self, msg: commands.AcceptAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            answering_player = game.get_answering_player()
            game.accept_answer(answering_player)
            user = await self.app.bot(msg.update).get_user(user_id=answering_player.user_id)
            await self.app.bot(msg.update).edit(
                f"Просто превосходно, {user.mention}! "
                f"Вы получаете {game.current_question.cost} очков!",
                remove_inline_keyboard=True
            )
            await self.app.bus.postpone(
                events.AnswerAccepted(msg.update), msg.update.origin, msg.update.chat_id, delay=2
            )
            await uow.commit()


class RejectAnswer(Handler):
    async def handler(self, msg: commands.RejectAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            answering_player = game.get_answering_player()
            game.reject_answer(answering_player)
            user = await self.app.bot(msg.update).get_user(user_id=answering_player.user_id)
            await self.app.bot(msg.update).edit(
                f"{user.mention}, к сожалению, ответ неверный, "
                f"вы теряете {game.current_question.cost} очков. "
                f"Кто-нибудь хочет ответить?",
                inline_keyboard=kb.make_answer_button()
            )
            await uow.commit()


class NextSelection(Handler):
    async def handler(self, msg: events.AnswerAccepted):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            player = game.get_current_player()
            user = await self.app.bot(msg.update).get_user(game.chat_id, player.user_id)
            await self.app.bot(msg.update).edit(
                f"{user.mention}, ваш черёд выбирать вопрос",
                inline_keyboard=kb.make_table(game.themes, game.selected_questions)
            )
            await uow.commit()


HANDLERS = {
    commands.Play: [GameCreator],
    commands.Join: [GameJoin],
    commands.CancelJoin: [GameCancelJoin],
    commands.Finish: [GameDestroyer],
    commands.StartGame: [GameStarter],
    commands.SelectQuestion: [QuestionSelector],
    commands.PressAnswerButton: [FirstPressedPlayer],
    commands.Answer: [PlayerAnswer],
    commands.PeekAnswer: [PeekAnswer],
    commands.RejectAnswer: [RejectAnswer],
    commands.AcceptAnswer: [AcceptAnswer],

    events.AnswerAccepted: [NextSelection]
}
