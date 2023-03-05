from sqlalchemy.exc import IntegrityError

from app.abc.handler import Handler
from app.bot.enums import Origin

from app.game import commands, events
from app.game.enums import GameState
from app.game.models import Game, Player
from app.game import keyboards as kb
from app.web.application import Application


class GameCreator(Handler):
    async def handler(self, msg: commands.Play):
        try:
            async with self.app.store.db() as uow:
                game = Game(
                    origin=msg.update.origin,
                    chat_id=msg.update.chat_id,
                    state=GameState.WAITING_FOR_LEADING
                )
                uow.games.add(game)
                await uow.commit()
        except IntegrityError as e:
            raise
        else:
            await self.app.bot(msg.update).send("Нам нужен ведущий.", kb.make_become_leading())


class GameLeading(Handler):
    async def handler(self, msg: commands.SetLeading):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_LEADING or game.leading_user_id is not None:
                return

            game.set_leading(msg.update.user_id)

            await self.app.bot(msg.update).callback("Вы теперь ведущий.")
            user = await self.app.bot(msg.update).get_user()
            await self.app.bot(msg.update).edit(
                f"Ведущий нашёлся - {user.mention}.",
                remove_inline_keyboard=True
            )
            await uow.commit()

        await self.app.bus.postpone(
            commands.StartRegistration(msg.update),
            msg.update.origin, msg.update.chat_id,
            delay=2
        )


class GameRegistration(Handler):
    async def handler(self, msg: commands.StartRegistration):
        await self.app.bot(msg.update).edit(
            f"Регистрация. Игроков зарегистрировано: 0",
            inline_keyboard=kb.make_registration()
        )


class GameDestroyer(Handler):
    async def handler(self, msg: commands.CancelGame):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if game is None:
                await self.app.bot(msg.update).send("Игры и так нет!")
                return

            if game.leading_user_id != msg.update.user_id:
                return

            game.finish()
            await uow.games.delete(msg.update.origin, msg.update.chat_id)
            await self.app.bot(msg.update).send("Игра досрочно завершена!")

            await uow.commit()


class GameJoin(Handler):
    async def handler(self, msg: commands.Join):
        try:
            async with self.app.store.db() as uow:

                game = await uow.games.get(msg.update.origin, msg.update.chat_id)

                if not game or game.state != GameState.REGISTRATION or game.leading_user_id == msg.update.user_id:
                    return

                game.register(
                    Player(origin=msg.update.origin, user_id=msg.update.user_id, chat_id=msg.update.chat_id))
                players_number = len(game.players)
                await uow.commit()

        except IntegrityError as e:
            if e.code == 'gkpj':
                pass
            else:
                raise
        else:
            await self.app.bot(msg.update).edit(
                f"Регистрация. Игроков зарегистрировано: {players_number}",
                inline_keyboard=kb.make_registration(players_number)
            )
            await self.app.bot(msg.update).callback("Вы зарегистрировались в игре!")


class GameCancelJoin(Handler):
    async def handler(self, msg: commands.CancelJoin):
        async with self.app.store.db() as uow:
            player = await uow.players.get(msg.update.origin, msg.update.chat_id, msg.update.user_id)

            if player is None:
                return

            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.REGISTRATION or game.leading_user_id == msg.update.user_id:
                return

            game.unregister(player)

            await self.app.bot(msg.update).edit(
                f"Регистрация. Игроков зарегистрировано: {len(game.players)}",
                inline_keyboard=kb.make_registration(len(game.players))
            )
            await self.app.bot(msg.update).callback("Вы ОТМЕНИЛИ регистрацию в игре!")
            await uow.commit()


class GameStarter(Handler):
    async def handler(self, msg: commands.StartGame):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.REGISTRATION or game.leading_user_id != msg.update.user_id:
                return

            themes = await uow.themes.list()
            player = game.start(themes)
            user = await self.app.bot(msg.update).get_user(game.chat_id, player.user_id)
            await uow.commit()

        text = f"Гадание на кофейной гуще привело к тому, что {user.mention} будет первым выбирать вопрос..."

        if msg.update.origin == Origin.TELEGRAM:
            self.app.bus.publish(commands.TelegramRenderQuestions(text=text, update=msg.update))
        else:
            self.app.bus.publish(commands.VkRenderQuestions(text=text, update=msg.update))


class QuestionSelector(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.QUESTION_SELECTION:
                return

            if len(game.selected_questions) == 5:
                self.app.bus.publish(commands.CancelGame(msg.update))
                return

            if game.current_user_id != msg.update.user_id:
                await self.app.bot(msg.update).callback("Не мешайте играть!!!")
                return

            question = game.select(msg.question_id)
            await self.app.bot(msg.update).edit(question.question, inline_keyboard=kb.make_answer_button())
            await uow.commit()


class PressButton(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        bot = self.app.bot(msg.update)
        async with self.app.store.db() as uow:
            player = await uow.players.get(msg.update.origin, msg.update.chat_id, msg.update.user_id)

            if player is None:
                await self.app.bot(msg.update).callback("Не мешайте играть!")
                return

            if player.already_answered:
                await self.app.bot(msg.update).callback("Вы уже отвечали!")
                return

            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_PRESS:
                return

            game.press(player)
            await bot.edit(remove_inline_keyboard=True)
            user = await bot.get_user()
            await bot.edit(
                f"{game.current_question.question}\n\n{user.mention}, вы всех опередили! Отвечайте.",
                remove_inline_keyboard=True
            )

            await uow.commit()


class Answer(Handler):
    async def handler(self, msg: commands.Answer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_ANSWER:
                return

            if game.answering_user_id != msg.update.user_id:
                return

            game.answer()

            await self.app.bot(msg.update).send("Что скажет ведущий?", kb.make_checker())

            await uow.commit()


class PeekAnswer(Handler):
    async def handler(self, msg: commands.PeekAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CHECKING or game.leading_user_id != msg.update.user_id:
                return

            await self.app.bot(msg.update).callback(f"{game.current_question.answer}")

            await uow.commit()


class AcceptAnswer(Handler):
    async def handler(self, msg: commands.AcceptAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CHECKING or game.leading_user_id != msg.update.user_id:
                return

            player = game.get_answering_player()

            if not player:
                return

            game.accept(player)

            user = await self.app.bot(msg.update).get_user(user_id=player.user_id)
            await self.app.bot(msg.update).edit(
                f"Просто превосходно, {user.mention}! "
                f"Вы получаете {game.current_question.cost} очков!",
                remove_inline_keyboard=True
            )

            await uow.commit()

        await self.app.bus.postpone(
            events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=2
        )


class RejectAnswer(Handler):
    async def handler(self, msg: commands.RejectAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CHECKING or game.leading_user_id != msg.update.user_id:
                return

            player = game.get_answering_player()

            if not player:
                return

            game.reject(player)

            user = await self.app.bot(msg.update).get_user(user_id=player.user_id)
            if game.is_all_answered():
                await self.app.bot(msg.update).edit(
                    f"{user.mention}, к сожалению, ответ неверный, "
                    f"вы теряете {game.current_question.cost} очков. "
                    f"Правильным ответом было: {game.current_question.answer}",
                    remove_inline_keyboard=True
                )
                await self.app.bus.postpone(
                    events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=3
                )
            else:
                await self.app.bot(msg.update).edit(
                    f"{user.mention}, к сожалению, ответ неверный, "
                    f"вы теряете {game.current_question.cost} очков. "
                    f"Кто-нибудь хочет ответить?",
                    inline_keyboard=kb.make_answer_button()
                )

            await uow.commit()


class NextSelection(Handler):
    async def handler(self, msg: events.QuestionFinished):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            if len(game.selected_questions) == 5:
                self.app.bus.publish(events.GameFinished(msg.update))
                return

            rows = ["Рейтинг на данный момент:\n"]
            for p in sorted(game.players, reverse=True, key=lambda player: player.points):
                user = await self.app.bot(msg.update).get_user(user_id=p.user_id)
                rows.append(f"{user.mention}: {p.points} очков")

            game.start_selection()

            await self.app.bot(msg.update).edit('\n'.join(rows), remove_inline_keyboard=True)

            user = await self.app.bot(msg.update).get_user(game.chat_id, game.current_user_id)
            text = f"{user.mention}, выбирайте вопрос: "
            if msg.update.origin == Origin.TELEGRAM:
                await self.app.bus.postpone(
                    commands.TelegramRenderQuestions(text=text, update=msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=3
                )
            else:
                await self.app.bus.postpone(
                    commands.VkRenderQuestions(text=text, update=msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=3
                )

            await uow.commit()


class Results(Handler):
    async def handler(self, msg: events.QuestionFinished):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            players = sorted(game.players, reverse=True, key=lambda player: player.points)
            winner = await self.app.bot(msg.update).get_user(user_id=players[0].user_id)
            rows = [f"ИГРА ЗАВЕРШЕНА!\nПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЯ: {winner.mention}!\n"]
            for p in sorted(game.players, reverse=True, key=lambda player: player.points):
                user = await self.app.bot(msg.update).get_user(user_id=p.user_id)
                rows.append(f"{user.mention}: {p.points} очков")

            game.finish()
            await uow.games.delete(msg.update.origin, msg.update.chat_id)
            await self.app.bot(msg.update).edit('\n'.join(rows), remove_inline_keyboard=True)

            await uow.commit()


class TelegramQuestionSelector(Handler):
    async def handler(self, msg: commands.TelegramRenderQuestions):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            await self.app.bot(msg.update).edit(
                msg.text,
                inline_keyboard=kb.make_table(game.themes, game.selected_questions)
            )


class VkQuestionSelector(Handler):
    async def handler(self, msg: commands.VkRenderQuestions):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            await self.app.bot(msg.update).edit(msg.text, remove_inline_keyboard=True)
            for t in game.themes:
                await self.app.bot(msg.update).send(
                    t.title, kb.make_vertical(t, game.selected_questions)
                )


def setup_handlers(app: Application):
    app.bus.register({
        commands.Play: [GameCreator],
        commands.CancelGame: [GameDestroyer],

        commands.SetLeading: [GameLeading],
        commands.StartRegistration: [GameRegistration],

        commands.Join: [GameJoin],
        commands.CancelJoin: [GameCancelJoin],

        commands.StartGame: [GameStarter],
        commands.SelectQuestion: [QuestionSelector],
        commands.PressButton: [PressButton],
        commands.Answer: [Answer],
        commands.PeekAnswer: [PeekAnswer],
        commands.RejectAnswer: [RejectAnswer],
        commands.AcceptAnswer: [AcceptAnswer],
        commands.VkRenderQuestions: [VkQuestionSelector],
        commands.TelegramRenderQuestions: [TelegramQuestionSelector],

        events.QuestionFinished: [NextSelection],
        events.GameFinished: [Results],

    })
