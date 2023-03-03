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
            if e.code == 'gkpj':
                await self.app.bot(msg.update).send("Игра уже начата!")
            else:
                raise
        else:
            await self.app.bot(msg.update).send("Нам нужен ведущий.", kb.make_become_leading())


class SetLeading(Handler):
    async def handler(self, msg: commands.SetLeading):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            if game.leading_user_id is not None:
                await self.app.bot(msg.update).callback("Ведущий уже выбран!")
            else:
                game.leading_user_id = msg.update.user_id
                await uow.commit()
            await self.app.bot(msg.update).callback("Вы теперь ведущий.")
            user = await self.app.bot(msg.update).get_user()
            await self.app.bot(msg.update).edit(
                f"Ведущий нашёлся - {user.mention}.",
                remove_inline_keyboard=True
            )
            await self.app.bus.postpone(
                commands.StartRegistration(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=2
            )


class Registration(Handler):
    async def handler(self, msg: commands.StartRegistration):
        await self.app.bot(msg.update).edit(
            f"Регистрация. Игроков зарегистрировано: 0",
            inline_keyboard=kb.make_registration()
        )


class GameDestroyer(Handler):
    async def handler(self, msg: commands.Finish):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if game is None:
                await self.app.bot(msg.update).send("Игры и так нет!")
                return

            if game.leading_user_id != msg.update.user_id:
                await self.app.bot(msg.update).send("Только ведущий может завершить игру!")
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

                if not game:
                    return

                if game.leading_user_id == msg.update.user_id:
                    await self.app.bot(msg.update).callback("Ведущий в регистрации не участвует!")
                    return

                game.register(
                    Player(origin=msg.update.origin, user_id=msg.update.user_id, chat_id=msg.update.chat_id))
                players_number = len(game.players)
                await uow.commit()

        except IntegrityError as e:
            if e.code == 'gkpj':
                await self.app.bot(msg.update).callback("Вы уже зарегистрированы!")
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
                await self.app.bot(msg.update).callback("Вы и так вне игры!")
                return

            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if game.leading_user_id == msg.update.user_id:
                await self.app.bot(msg.update).callback("Ведущий в регистрации не участвует!")
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

            if not game:
                return

            if game.leading_user_id != msg.update.user_id:
                await self.app.bot(msg.update).callback("Только ведущий может досрочно начать игру!")
                return

            themes = await uow.themes.list()

            player = game.start(themes)

            user = await self.app.bot(msg.update).get_user(game.chat_id, player.user_id)

            if msg.update.origin == Origin.TELEGRAM:
                await self.app.bot(msg.update).edit(
                    f"Гадание на кофейной гуще привело к тому, "
                    f"что {user.mention} будет первым выбирать вопрос...",
                    inline_keyboard=kb.make_table(game.themes, game.selected_questions))
            else:
                await self.app.bot(msg.update).edit(
                    f"Гадание на кофейной гуще привело к тому, "
                    f"что {user.mention} будет первым выбирать вопрос...")
                for t in game.themes:
                    await self.app.bot(msg.update).send(
                        t.title, kb.make_row(t, game.selected_questions)
                    )

            await uow.commit()


class QuestionSelector(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            if not game:
                return

            if len(game.selected_questions) == 5:
                self.app.bus.publish(commands.Finish(msg.update))
                return

            if game.current_user_id != msg.update.user_id:
                await self.app.bot(msg.update).callback("Не мешайте играть!!!")
                return

            question = game.select(msg.question_id)
            await self.app.bot(msg.update).edit(question.question, inline_keyboard=kb.make_answer_button())
            await uow.commit()


class FirstPressedPlayer(Handler):
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

            game.press(player)

            await uow.commit()

        user = await bot.get_user()
        await bot.edit(remove_inline_keyboard=True)
        await bot.send(f"{user.mention}, вы всех опередили! Отвечайте.")


class PlayerAnswer(Handler):
    async def handler(self, msg: commands.Answer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if game.state != GameState.WAITING_FOR_ANSWER:
                return

            if game.answering_user_id != msg.update.user_id:
                return

            game.answer()

            await uow.commit()

        await self.app.bot(msg.update).send("Что скажет ведущий?", kb.make_checker())


class PeekAnswer(Handler):
    async def handler(self, msg: commands.PeekAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)
            if game.leading_user_id != msg.update.user_id:
                return await self.app.bot(msg.update).callback()
            await self.app.bot(msg.update).callback(f"{game.current_question.answer}")
            await uow.commit()


class AcceptAnswer(Handler):
    async def handler(self, msg: commands.AcceptAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            if game.leading_user_id != msg.update.user_id:
                return await self.app.bot(msg.update).callback()
            player = game.accept()
            user = await self.app.bot(msg.update).get_user(user_id=player.user_id)
            await self.app.bot(msg.update).edit(
                f"Просто превосходно, {user.mention}! "
                f"Вы получаете {game.current_question.cost} очков!",
                remove_inline_keyboard=True
            )
            await self.app.bus.postpone(
                events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=2
            )
            await uow.commit()


class RejectAnswer(Handler):
    async def handler(self, msg: commands.RejectAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game:
                return

            if game.leading_user_id != msg.update.user_id:
                return await self.app.bot(msg.update).callback()
            player = game.reject()
            if game.is_all_answered():
                await self.app.bot(msg.update).edit(
                    f"Правильным ответом было: {game.current_question.answer}",
                    remove_inline_keyboard=True
                )
                await self.app.bus.postpone(
                    events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=2
                )
            else:
                user = await self.app.bot(msg.update).get_user(user_id=player.user_id)
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

            game.start_selection()

            user = await self.app.bot(msg.update).get_user(game.chat_id, game.current_user_id)
            await self.app.bot(msg.update).edit(
                f"{user.mention}, ваш черёд выбирать вопрос",
                inline_keyboard=kb.make_table(game.themes, game.selected_questions)
            )
            await uow.commit()


def setup_handlers(app: Application):
    app.bus.register({
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
        commands.StartRegistration: [Registration],
        commands.SetLeading: [SetLeading],

        events.QuestionFinished: [NextSelection],
    })
