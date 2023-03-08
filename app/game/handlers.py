from random import choice

from sqlalchemy.exc import IntegrityError

from app.abc.handler import Handler
from app.bot.enums import Origin

from app.game import commands, events, tools
from app.game.enums import GameState, Delay
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

                message_id = await self.app.bot(msg.update).send(
                    f"Нам нужен ведущий. ({Delay.WAIT_LEADING} сек.)",
                    kb.make_become_leading()
                )
                await self.app.bus.postpone_publish(
                    events.WaitingForLeadingTimeout(msg.update, message_id),
                    msg.update.origin, msg.update.chat_id,
                    delay=Delay.WAIT_LEADING
                )

        except IntegrityError:
            pass


class GameLeading(Handler):
    async def handler(self, msg: commands.SetLeading):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_LEADING or game.leading_user_id is not None:
                return

            await self.app.bus.cancel(events.WaitingForLeadingTimeout, msg.update.origin, msg.update.chat_id)

            game.set_leading(msg.update.user_id)

            await uow.commit()

            user = await self.app.bot(msg.update).get_user()
            await self.app.bot(msg.update).edit(
                f"Ведущий нашёлся - {user.mention}.",
                remove_inline_keyboard=True
            )

            await self.app.bus.postpone_publish(
                commands.StartRegistration(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.PAUSE
            )


class GameRegistration(Handler):
    async def handler(self, msg: commands.StartRegistration):
        await self.app.bot(msg.update).edit(
            f"Регистрация. Игроков зарегистрировано: 0.\n({Delay.REGISTRATION} сек.)",
            inline_keyboard=kb.make_registration()
        )
        await self.app.bus.postpone_publish(
            events.RegistrationTimeout(msg.update, msg.update.message_id),
            msg.update.origin, msg.update.chat_id,
            delay=Delay.REGISTRATION
        )


class GameDestroyer(Handler):
    async def handler(self, msg: commands.CancelGame):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                await self.app.bot(msg.update).send("Игры и так нет!")
                return

            if game.leading_user_id != msg.update.user_id:
                return

            game.finish()
            await uow.games.delete(msg.update.origin, msg.update.chat_id)

            await uow.commit()

            if game.state not in (GameState.REGISTRATION, GameState.WAITING_FOR_LEADING):
                await self.app.bot(msg.update).send(
                    f"ИГРА ДОСРОЧНО ЗАВЕРШЕНА!\n\n"
                    f"РЕЙТИНГ ИГРОВОЙ СЕССИИ:\n\n" + tools.players_rating(game.players)
                )
            else:
                await self.app.bot(msg.update).send("ИГРА ДОСРОЧНО ЗАВЕРШЕНА!")


class GameJoin(Handler):
    async def handler(self, msg: commands.Join):
        try:
            async with self.app.store.db() as uow:

                game = await uow.games.get(msg.update.origin, msg.update.chat_id)

                if not game or game.state != GameState.REGISTRATION or game.leading_user_id == msg.update.user_id:
                    return

                game.register(
                    Player(
                        origin=msg.update.origin,
                        user_id=msg.update.user_id,
                        chat_id=msg.update.chat_id,
                        name=(await self.app.bot(msg.update).get_user()).mention
                    )
                )

                await uow.commit()

                await self.app.bot(msg.update).edit(
                    tools.players_list(game.players) + f"\n({Delay.REGISTRATION} сек.)",
                    inline_keyboard=kb.make_registration(len(game.players))
                )

        except IntegrityError as e:
            if e.code == 'gkpj':
                pass


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

            await uow.commit()

            await self.app.bot(msg.update).edit(
                tools.players_list(game.players) + f"\n({Delay.REGISTRATION} сек.)",
                inline_keyboard=kb.make_registration(len(game.players))
            )


class GameStarter(Handler):
    async def handler(self, msg: commands.StartGame):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.REGISTRATION or game.leading_user_id != msg.update.user_id:
                return

            await self.app.bus.cancel(events.RegistrationTimeout, msg.update.origin, msg.update.chat_id)

            themes = await uow.themes.list()
            player = game.start(themes)

            await uow.commit()

            text = f"Звёзды сказали, что {player.name} будет первым выбирать вопрос...\n({Delay.WAIT_SELECTION} сек.)"

            if msg.update.origin == Origin.TELEGRAM:
                self.app.bus.publish(commands.TelegramRenderQuestions(text=text, update=msg.update))
            else:
                self.app.bus.publish(commands.VkRenderQuestions(text=text, update=msg.update))


class QuestionSelector(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.QUESTION_SELECTION or game.current_user_id != msg.update.user_id:
                return

            await self.app.bus.cancel(events.WaitingSelectionTimeout, msg.update.origin, msg.update.chat_id)

            question = game.select(msg.question_id)

            await uow.commit()

            if msg.update.origin == Origin.VK:
                await self.app.bus.cancel(commands.HideQuestionsTimeout, msg.update.origin, msg.update.chat_id)
                await self.app.bus.force_publish(commands.HideQuestions, msg.update.origin, msg.update.chat_id)
            else:
                await self.app.bot(msg.update).edit(
                    f"Вопрос за {question.cost}:\n{question.question}\n({Delay.WAIT_PRESS} сек.)",
                    inline_keyboard=kb.make_answer_button()
                )
                await self.app.bus.postpone_publish(
                    events.WaitingPressTimeout(msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.WAIT_PRESS
                )


class PressButton(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        bot = self.app.bot(msg.update)
        async with self.app.store.db() as uow:
            player = await uow.players.get(msg.update.origin, msg.update.chat_id, msg.update.user_id)

            if player is None or player.already_answered:
                return

            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_PRESS:
                return

            await self.app.bus.cancel(events.WaitingPressTimeout, msg.update.origin, msg.update.chat_id)

            game.press(player)

            await uow.commit()

            await bot.edit(
                f"{game.current_question.question}\n\n{player.name}, вы всех опередили! Отвечайте."
                f"\n({Delay.WAIT_ANSWER} сек.)",
                remove_inline_keyboard=True
            )

            await self.app.bus.postpone_publish(
                events.WaitingForAnswerTimeout(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.WAIT_ANSWER
            )


class Answer(Handler):
    async def handler(self, msg: commands.Answer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_ANSWER or game.answering_user_id != msg.update.user_id:
                return

            await self.app.bus.cancel(events.WaitingForAnswerTimeout, msg.update.origin, msg.update.chat_id)

            game.answer()

            await uow.commit()

            message_id = await self.app.bot(msg.update).send(
                f"Что скажет ведущий?\n({Delay.WAIT_CHECKING} сек.)",
                kb.make_checker()
            )

            await self.app.bus.postpone_publish(
                events.WaitingForCheckingTimeout(msg.update, message_id),
                msg.update.origin,
                msg.update.chat_id,
                delay=Delay.WAIT_CHECKING
            )


class PeekAnswer(Handler):
    async def handler(self, msg: commands.PeekAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CHECKING or game.leading_user_id != msg.update.user_id:
                return

            await self.app.bot(msg.update).callback(f"{game.current_question.answer}")


class AcceptAnswer(Handler):
    async def handler(self, msg: commands.AcceptAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CHECKING or game.leading_user_id != msg.update.user_id:
                return

            if not (player := game.get_answering_player()):
                return

            await self.app.bus.cancel(events.WaitingForCheckingTimeout, msg.update.origin, msg.update.chat_id)

            game.accept(player)

            await uow.commit()

            await self.app.bot(msg.update).edit(
                f"Просто превосходно, {player.name}! "
                f"Вы получаете {game.current_question.cost} очков!",
                remove_inline_keyboard=True
            )

            await self.app.bus.postpone_publish(
                events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=Delay.PAUSE
            )


class RejectAnswer(Handler):
    async def handler(self, msg: commands.RejectAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CHECKING or game.leading_user_id != msg.update.user_id:
                return

            if not (player := game.get_answering_player()):
                return

            await self.app.bus.cancel(events.WaitingForCheckingTimeout, msg.update.origin, msg.update.chat_id)

            game.reject(player)

            await uow.commit()

            if game.is_all_answered():
                await self.app.bot(msg.update).edit(
                    f"{player.name}, к сожалению, ответ неверный, "
                    f"вы теряете {game.current_question.cost} очков.\n"
                    f"Правильным ответом было: «{game.current_question.answer}».",
                    remove_inline_keyboard=True
                )
                await self.app.bus.postpone_publish(
                    events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=Delay.PAUSE
                )
            else:
                await self.app.bot(msg.update).edit(
                    f"{player.name}, к сожалению, ответ неверный, "
                    f"вы теряете {game.current_question.cost} очков.\n"
                    f"Кто-нибудь хочет ответить?\n({Delay.WAIT_PRESS} сек.)",
                    inline_keyboard=kb.make_answer_button()
                )
                await self.app.bus.postpone_publish(
                    events.WaitingPressTimeout(msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.WAIT_PRESS
                )


class NextSelection(Handler):
    async def handler(self, msg: events.QuestionFinished):
        async with self.app.store.db() as uow:

            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            if not game.any_questions():
                self.app.bus.publish(events.GameFinished(msg.update))
                return

            await self.app.bus.cancel(events.WaitingForCheckingTimeout, msg.update.origin, msg.update.chat_id)

            current_player = game.start_selection()

            await uow.commit()

            await self.app.bot(msg.update).edit(
                "Рейтинг на данный момент:\n\n" + tools.players_rating(game.players),
                remove_inline_keyboard=True
            )

            text = f"{current_player.name}, выбирайте вопрос.\n({Delay.WAIT_SELECTION} сек.)"
            if msg.update.origin == Origin.TELEGRAM:
                await self.app.bus.postpone_publish(
                    commands.TelegramRenderQuestions(text=text, update=msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.PAUSE
                )
            else:
                await self.app.bus.postpone_publish(
                    commands.VkRenderQuestions(text=text, update=msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.PAUSE
                )


class Results(Handler):
    async def handler(self, msg: events.QuestionFinished):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            game.finish()

            await uow.games.delete(msg.update.origin, msg.update.chat_id)
            await uow.commit()

            await self.app.bot(msg.update).edit(
                f"ИГРА ЗАВЕРШЕНА!\n\nПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЯ: "
                f"{max(game.players, key=lambda p: p.points).name}!\n\n" + tools.players_rating(game.players),
                remove_inline_keyboard=True
            )


class TelegramQuestionSelector(Handler):
    async def handler(self, msg: commands.TelegramRenderQuestions):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            await self.app.bot(msg.update).edit(
                msg.text,
                inline_keyboard=kb.make_table(game.themes, game.selected_questions)
            )

            await self.app.bus.postpone_publish(
                events.WaitingSelectionTimeout(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.WAIT_SELECTION
            )


class VkQuestionSelector(Handler):
    async def handler(self, msg: commands.VkRenderQuestions):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            message_ids = []
            await self.app.bot(msg.update).edit(msg.text, remove_inline_keyboard=True)
            for t in game.themes:
                message_ids.append(await self.app.bot(msg.update).send(
                    t.title, kb.make_vertical(t, game.selected_questions)
                ))

            await self.app.bus.postpone_publish(
                events.WaitingSelectionTimeout(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.WAIT_SELECTION
            )
            await self.app.bus.postpone_publish(
                commands.HideQuestions(msg.update, message_ids),
                msg.update.origin,
                msg.update.chat_id,
                delay=100
            )
            await self.app.bus.postpone_publish(
                commands.HideQuestionsTimeout(msg.update, message_ids),
                msg.update.origin,
                msg.update.chat_id,
                delay=100
            )


class HideQuestions(Handler):
    async def handler(self, msg: commands.HideQuestions):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            for message_id in msg.message_ids:
                await self.app.bot(msg.update).delete(message_id)

            await self.app.bot(msg.update).edit(
                f"Вопрос за {game.current_question.cost}:\n{game.current_question.question}"
                f"\n({Delay.WAIT_PRESS} сек.)",
                inline_keyboard=kb.make_answer_button()
            )

            await self.app.bus.postpone_publish(
                events.WaitingPressTimeout(msg.update),
                msg.update.origin,
                msg.update.chat_id,
                delay=Delay.WAIT_PRESS
            )


class HideQuestionsTimeout(Handler):
    async def handler(self, msg: commands.HideQuestionsTimeout):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            for message_id in msg.message_ids:
                await self.app.bot(msg.update).delete(message_id)

            await self.app.bot(msg.update).edit(
                f"Время на выбор вопросы истекло.\n"
                f"Вопрос за {game.current_question.cost} выбран случайно:\n{game.current_question.question}"
                f"\n({Delay.WAIT_PRESS} сек.)", inline_keyboard=kb.make_answer_button()
            )

            await self.app.bus.postpone_publish(
                events.WaitingPressTimeout(msg.update),
                msg.update.origin,
                msg.update.chat_id,
                delay=Delay.WAIT_PRESS
            )


class CheckingTimeout(Handler):
    async def handler(self, msg: events.WaitingForCheckingTimeout):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            game.finish()

            await uow.games.delete(msg.update.origin, msg.update.chat_id)
            await uow.commit()

            await self.app.bot(msg.update).edit(
                f"Кажется ведущий оставил нас...\n\nИГРА ОТМЕНЕНА!\n\n"
                f"Рейтинг игровой сессии:\n\n" + tools.players_rating(game.players),
                remove_inline_keyboard=True,
                message_id=msg.message_id
            )


class InitGameTimeout(Handler):
    async def handler(self, msg: events.WaitingForLeadingTimeout):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            game.finish()
            await uow.games.delete(msg.update.origin, msg.update.chat_id)

            await uow.commit()

            await self.app.bot(msg.update).edit(
                "Время истекло, игра отменена!",
                remove_inline_keyboard=True,
                message_id=msg.message_id
            )


class SelectionTimeout(Handler):
    async def handler(self, msg: events.WaitingSelectionTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.QUESTION_SELECTION:
                return

            questions_ids = tuple({q.id for t in game.themes for q in t.questions} - set(game.selected_questions))

            question = game.select(choice(questions_ids))

            await uow.commit()

            if msg.update.origin == Origin.VK:
                await self.app.bus.force_publish(commands.HideQuestionsTimeout, msg.update.origin, msg.update.chat_id)
                await self.app.bus.cancel(commands.HideQuestions, msg.update.origin, msg.update.chat_id)
            else:
                await self.app.bot(msg.update).edit(
                    f"Время на выбор вопросы истекло. "
                    f"Вопрос за {question.cost} выбран случайно:\n{question.question}\n({Delay.WAIT_PRESS} сек.)",
                    inline_keyboard=kb.make_answer_button()
                )

                await self.app.bus.postpone_publish(
                    events.WaitingPressTimeout(msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.WAIT_PRESS
                )


class PressTimeout(Handler):
    async def handler(self, msg: events.WaitingPressTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_PRESS:
                return

            await uow.commit()

            await self.app.bot(msg.update).edit(
                f"Никто не соизволил дать ответ...\n\nПравильным ответом было: «{game.current_question.answer}».",
                remove_inline_keyboard=True
            )
            await self.app.bus.postpone_publish(
                events.QuestionFinished(msg.update),
                msg.update.origin,
                msg.update.chat_id,
                delay=Delay.PAUSE
            )


class AnswerTimeout(Handler):
    async def handler(self, msg: events.WaitingForAnswerTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_ANSWER:
                return

            if not (player := game.get_answering_player()):
                return

            game.reject(player)

            await uow.commit()

            if game.is_all_answered():
                await self.app.bot(msg.update).edit(
                    f"{player.name}, ваше время на ответ истекло.\n"
                    f"Вы теряете {game.current_question.cost} очков.\n"
                    f"Правильным ответом было: «{game.current_question.answer}».",
                    remove_inline_keyboard=True
                )
                await self.app.bus.postpone_publish(
                    events.QuestionFinished(msg.update), msg.update.origin, msg.update.chat_id, delay=3
                )
            else:
                await self.app.bot(msg.update).edit(
                    f"{player.name}, ваше время на ответ истекло.\n"
                    f"Вы теряете {game.current_question.cost} очков. "
                    f"Кто-нибудь хочет ответить?\n({Delay.WAIT_PRESS} сек.)",
                    inline_keyboard=kb.make_answer_button()
                )
                await self.app.bus.postpone_publish(
                    events.WaitingPressTimeout(msg.update),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.WAIT_PRESS
                )


class ShowPhoto(Handler):
    async def handler(self, msg: commands.ShowPhoto):
        await self.app.bot(msg.update).send_photo(msg.path, "🔍 Внимательно посмотрите на изображение.")


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
        commands.HideQuestions: [HideQuestions],
        commands.HideQuestionsTimeout: [HideQuestionsTimeout],

        events.QuestionFinished: [NextSelection],
        events.GameFinished: [Results],
        events.WaitingForLeadingTimeout: [InitGameTimeout],
        events.RegistrationTimeout: [InitGameTimeout],
        events.WaitingSelectionTimeout: [SelectionTimeout],
        events.WaitingPressTimeout: [PressTimeout],
        events.WaitingForAnswerTimeout: [AnswerTimeout],
        events.WaitingForCheckingTimeout: [CheckingTimeout]
    })
