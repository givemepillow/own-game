from random import choice

from sqlalchemy.exc import IntegrityError

from app.abc.handler import Handler
from app.bot.enums import Origin

from app.game import commands, events, tools, texts
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
                    f"🫵 Нам нужен ведущий.\n\n{texts.delay(Delay.WAIT_LEADING)}",
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
            await self.app.bot(msg.update).edit(f"💥 Ведущий нашёлся - {user.mention}.")

            await self.app.bus.postpone_publish(
                commands.StartRegistration(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.LITTLE_PAUSE
            )


class GameRegistration(Handler):
    async def handler(self, msg: commands.StartRegistration):
        await self.app.bot(msg.update).edit(
            tools.players_list([]) + f"\n\n{texts.delay(Delay.REGISTRATION)}",
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

            if game.leading_user_id != msg.update.user_id and game.leading_user_id is not None:
                return

            game.finish()
            await uow.games.delete(msg.update.origin, msg.update.chat_id)

            await uow.commit()

            if game.state not in (GameState.REGISTRATION, GameState.WAITING_FOR_LEADING):
                await self.app.bot(msg.update).send(
                    f"🔌 ИГРА ДОСРОЧНО ЗАВЕРШЕНА!\n\n"
                    f"📊 РЕЙТИНГ ИГРОВОЙ СЕССИИ:\n\n" + tools.players_rating(game.players)
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

                user = await self.app.bot(msg.update).get_user()

                game.register(Player(
                    origin=msg.update.origin,
                    user_id=msg.update.user_id,
                    chat_id=msg.update.chat_id,
                    name=user.name,
                    username=user.username
                ))

                await uow.commit()

                await self.app.bot(msg.update).edit(
                    tools.players_list(game.players) + f"\n\n{texts.delay(Delay.REGISTRATION)}",
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
                tools.players_list(game.players) + f"\n\n{texts.delay(Delay.REGISTRATION)}",
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
            current_player = game.start(themes)

            await uow.commit()

            text = f"🔮 Так сошлись звезды...\n\n" \
                   f"{current_player.mention} будет первым выбирать вопрос." \
                   f"\n\n{texts.delay(Delay.WAIT_SELECTION)}"

            if msg.update.origin == Origin.TELEGRAM:
                self.app.bus.publish(commands.TelegramRenderQuestions(msg.update, text, msg.update.message_id))
            else:
                self.app.bus.publish(commands.VkRenderQuestions(msg.update, text, msg.update.message_id))


class QuestionSelector(Handler):
    async def handler(self, msg: commands.SelectQuestion):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.QUESTION_SELECTION or game.current_user_id != msg.update.user_id:
                return

            await self.app.bus.cancel(events.WaitingSelectionTimeout, msg.update.origin, msg.update.chat_id)

            question, theme = game.select(msg.question_id)

            await uow.commit()

            current_player = game.get_current_player()

            await self.app.bus.force_publish(commands.HideQuestions, msg.update.origin, msg.update.chat_id)

            text = f"📌 {current_player.link} выбрал(a) «{theme.title} за {question.cost}»."

            if game.is_cat_in_bag():
                text += f"\n\n🐈🐈‍⬛🐈🐈‍⬛🐈🐈‍⬛🐈🐈‍⬛🐈🐈‍⬛\n\n🐱 А это оказался кот в мешке!!!"
                await self.app.bus.postpone_publish(
                    events.CatInBag(msg.update, msg.update.message_id),
                    msg.update.origin, msg.update.chat_id, delay=Delay.LITTLE_PAUSE
                )
            else:
                await self.app.bus.postpone_publish(
                    commands.ShowQuestion(msg.update),
                    msg.update.origin, msg.update.chat_id,
                    delay=Delay.PAUSE
                )

                await self.app.bus.postpone_publish(
                    commands.ShowPress(
                        msg.update,
                        f"🧐 Кто будет отвечать?\n\n{texts.delay(tools.question_delay(game))}"
                    ),
                    msg.update.origin, msg.update.chat_id,
                    delay=tools.question_delay(game) + Delay.PAUSE
                )

            if msg.update.origin == Origin.VK:
                await self.app.bot(msg.update).send(text)
            else:
                await self.app.bot(msg.update).edit(text, message_id=msg.update.message_id)


class ShowQuestion(Handler):
    async def handler(self, msg: commands.ShowQuestion):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game.current_question.filename:
                await self.app.bot(msg.update).send(
                    f"📖 Вопрос за {game.current_question.cost}:\n\n"
                    f"❔ {game.current_question.question}"
                )
            elif game.current_question.content_type.startswith('image'):
                await self.app.bot(msg.update).send_photo(
                    self.app.store.path(game.current_question.filename),
                    f"🖼 Вопрос с картинкой за {game.current_question.cost}:\n\n"
                    f"❔ {game.current_question.question}"
                )
            elif game.current_question.content_type.startswith('audio'):
                await self.app.bot(msg.update).send_voice(
                    self.app.store.path(game.current_question.filename),
                    f"🎧 Аудио вопрос за {game.current_question.cost}:\n\n"
                    f"❔ {game.current_question.question}"
                )
            elif game.current_question.content_type.startswith('video'):
                await self.app.bot(msg.update).send_voice(
                    self.app.store.path(game.current_question.filename),
                    f"🎥 Видео вопрос за {game.current_question.cost}:\n\n"
                    f"❔ {game.current_question.question}"
                )


class ShowPress(Handler):
    async def handler(self, msg: commands.ShowPress):
        message_id = await self.app.bot(msg.update).send(msg.text, kb.make_answer_button())
        await self.app.bus.postpone_publish(
            events.WaitingPressTimeout(msg.update, message_id),
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

            await bot.edit(f"🚀 {player.mention}, вы всех опередили! Отвечайте.\n\n{texts.delay(Delay.WAIT_ANSWER)}")

            await self.app.bus.postpone_publish(
                events.WaitingForAnswerTimeout(msg.update, msg.update.message_id),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.WAIT_ANSWER
            )


class Answer(Handler):
    async def handler(self, msg: commands.Answer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.answering_user_id != msg.update.user_id:
                return

            if game.state not in (GameState.WAITING_FOR_ANSWER, GameState.WAITING_FOR_CAT_IN_BAG_ANSWER):
                return

            game.answer()

            await self.app.bus.cancel(events.WaitingForAnswerTimeout, msg.update.origin, msg.update.chat_id)

            await uow.commit()

            message_id = await self.app.bot(msg.update).send(
                f"Что скажет {game.leading_link}? 🤔\n\n{texts.delay(Delay.WAIT_CHECKING)}",
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

            if not game or game.leading_user_id != msg.update.user_id:
                return

            await self.app.bot(msg.update).callback(f"{game.current_question.answer}")


class AcceptAnswer(Handler):
    async def handler(self, msg: commands.AcceptAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.leading_user_id != msg.update.user_id:
                return

            if not (player := game.get_answering_player()):
                return

            if game.state not in (GameState.WAITING_FOR_CAT_IN_BAG_CHECKING, GameState.WAITING_FOR_CHECKING):
                return

            await self.app.bus.cancel(events.WaitingForCheckingTimeout, msg.update.origin, msg.update.chat_id)

            game.accept(player)

            await uow.commit()

            await self.app.bot(msg.update).edit(
                f"💯 Просто превосходно, {player.link}!\n\n"
                f"📈 Вы получаете {tools.convert_number(game.current_question.cost)} очков!"
            )

            await self.app.bus.postpone_publish(
                events.QuestionFinished(msg.update, msg.update.message_id),
                msg.update.origin,
                msg.update.chat_id,
                delay=Delay.PAUSE
            )


class RejectAnswer(Handler):
    async def handler(self, msg: commands.RejectAnswer):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.leading_user_id != msg.update.user_id:
                return

            if not (player := game.get_answering_player()):
                return

            if game.state not in (GameState.WAITING_FOR_CAT_IN_BAG_CHECKING, GameState.WAITING_FOR_CHECKING):
                return

            await self.app.bus.cancel(events.WaitingForCheckingTimeout, msg.update.origin, msg.update.chat_id)

            game.reject(player)

            await uow.commit()

            if game.state != GameState.WAITING_FOR_PRESS:
                await self.app.bot(msg.update).edit(
                    f"{player.link}, к сожалению, ответ неверный... 😔\n\n"
                    f"📉 Вы теряете {tools.convert_number(game.current_question.cost)} очков.\n\n"
                    f"👉 Правильным ответом было: «{game.current_question.answer}»."
                )
                await self.app.bus.postpone_publish(
                    events.QuestionFinished(msg.update, msg.update.message_id),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.PAUSE
                )
            else:
                await self.app.bot(msg.update).edit(
                    f"{player.link}, к сожалению, ответ неверный... 😔\n\n"
                    f"📉 Вы теряете {tools.convert_number(game.current_question.cost)} очков.\n\n"
                    f"⚠️ Кто-нибудь хочет ответить?\n\n{texts.delay(Delay.WAIT_PRESS)}",
                    inline_keyboard=kb.make_answer_button()
                )
                await self.app.bus.postpone_publish(
                    events.WaitingPressTimeout(msg.update, msg.update.message_id),
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
                self.app.bus.publish(events.GameFinished(msg.update, msg.message_id))
                return

            await self.app.bus.cancel(events.WaitingForCheckingTimeout, msg.update.origin, msg.update.chat_id)

            current_player = game.start_selection()

            await uow.commit()

            await self.app.bot(msg.update).edit(
                "📊 Рейтинг на данный момент:\n\n" + tools.players_rating(game.players),
                message_id=msg.message_id
            )

            text = f"{current_player.mention}, выбирайте вопрос.\n\n{texts.delay(Delay.WAIT_SELECTION)}"
            if msg.update.origin == Origin.TELEGRAM:
                await self.app.bus.postpone_publish(
                    commands.TelegramRenderQuestions(msg.update, text, msg.message_id),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.PAUSE
                )
            else:
                await self.app.bus.postpone_publish(
                    commands.VkRenderQuestions(msg.update, text, msg.message_id),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.PAUSE
                )


class TelegramQuestionSelector(Handler):
    async def handler(self, msg: commands.TelegramRenderQuestions):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            await self.app.bot(msg.update).edit(
                msg.text,
                inline_keyboard=kb.make_table(game.themes, game.selected_questions),
                message_id=msg.message_id
            )

            await self.app.bus.postpone_publish(
                events.WaitingSelectionTimeout(msg.update, msg.message_id),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.WAIT_SELECTION
            )


class VkQuestionSelector(Handler):
    async def handler(self, msg: commands.VkRenderQuestions):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            await self.app.bot(msg.update).edit(
                msg.text,

                message_id=msg.message_id
            )
            message_ids = [msg.message_id]
            for t in game.themes:
                message_ids.append(await self.app.bot(msg.update).send(
                    t.title, kb.make_vertical(t, game.selected_questions)
                ))

            await self.app.bus.postpone_publish(
                events.WaitingSelectionTimeout(msg.update, msg.message_id),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.WAIT_SELECTION
            )
            await self.app.bus.postpone_publish(
                commands.HideQuestions(msg.update, message_ids),
                msg.update.origin,
                msg.update.chat_id,
                delay=100
            )


class HideQuestions(Handler):
    async def handler(self, msg: commands.HideQuestions):
        for message_id in msg.message_ids:
            await self.app.bot(msg.update).delete(message_id)


class Results(Handler):
    async def handler(self, msg: events.GameFinished):
        async with self.app.store.db() as uow:
            if not (game := await uow.games.get(msg.update.origin, msg.update.chat_id)):
                return

            game.finish()

            await uow.games.delete(msg.update.origin, msg.update.chat_id)
            await uow.commit()

            await self.app.bot(msg.update).edit(
                f"🎉🎊 ИГРА ЗАВЕРШЕНА!!! 🎊🎉\n\n👑 ПОЗДРАВЛЯЕМ ПОБЕДИТЕЛЯ: "
                f"{max(game.players, key=lambda p: p.points).link}!\n\n" + tools.players_rating(game.players),
                message_id=msg.message_id
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
                f"Кажется {game.leading_link} оставил нас... 🤡\n\nИГРА ОТМЕНЕНА!\n\n"
                f"Рейтинг игровой сессии:\n\n" + tools.players_rating(game.players),

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

            await self.app.bot(msg.update).edit("⏳ Время истекло, игра отменена!", message_id=msg.message_id)


class SelectionTimeout(Handler):
    async def handler(self, msg: events.WaitingSelectionTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.QUESTION_SELECTION:
                return

            questions_ids = tuple(
                {q.id for t in game.themes for q in t.questions} - set(game.selected_questions)
            )

            question, theme = game.select(choice(questions_ids))

            await uow.commit()

            await self.app.bus.force_publish(commands.HideQuestions, msg.update.origin, msg.update.chat_id)

            text = f"⏳ ВРЕМЯ НА ВЫБОР ВОПРОСА ИСТЕКЛО.\n\n" \
                   f"🎲 Случайный вопрос:  «{theme.title} за {question.cost}»."

            await self.app.bus.postpone_publish(
                commands.ShowQuestion(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.LITTLE_PAUSE
            )

            await self.app.bus.postpone_publish(
                commands.ShowPress(
                    msg.update,
                    f"🧐 Кто будет отвечать?\n\n{texts.delay(tools.question_delay(game))}"
                ),
                msg.update.origin, msg.update.chat_id,
                delay=tools.question_delay(game) + Delay.PAUSE
            )

            if msg.update.origin == Origin.TELEGRAM:
                await self.app.bot(msg.update).edit(text, message_id=msg.message_id)
            else:
                await self.app.bot(msg.update).send(text)


class PressTimeout(Handler):
    async def handler(self, msg: events.WaitingPressTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_PRESS:
                return

            await self.app.bot(msg.update).edit(
                f"Никто не соизволил дать ответ... 🤌\n\nПравильным ответом было: «{game.current_question.answer}».",
                message_id=msg.message_id
            )
            await self.app.bus.postpone_publish(
                events.QuestionFinished(msg.update, msg.message_id),
                msg.update.origin,
                msg.update.chat_id,
                delay=Delay.PAUSE
            )


class AnswerTimeout(Handler):
    async def handler(self, msg: events.WaitingForAnswerTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state not in (GameState.WAITING_FOR_ANSWER, GameState.WAITING_FOR_CAT_IN_BAG_ANSWER):
                return

            if not (player := game.get_answering_player()):
                return

            game.reject(player)

            await uow.commit()

            if game.state != GameState.WAITING_FOR_PRESS:
                await self.app.bot(msg.update).edit(
                    f"⏳ {player.link}, ваше время на ответ истекло.\n\n"
                    f"📉 Вы теряете {tools.convert_number(game.current_question.cost)} очков.\n\n"
                    f"👉 Правильным ответом было: «{game.current_question.answer}».",
                    message_id=msg.message_id
                )
                await self.app.bus.postpone_publish(
                    events.QuestionFinished(msg.update, msg.message_id),
                    msg.update.origin, msg.update.chat_id, delay=Delay.PAUSE
                )
            else:
                await self.app.bot(msg.update).edit(
                    f"⏳ {player.link}, ваше время на ответ истекло.\n\n"
                    f"📉 Вы теряете {tools.convert_number(game.current_question.cost)} очков.\n\n"
                    f"⚠️ Кто-нибудь хочет ответить?\n\n{texts.delay(Delay.WAIT_PRESS)}",
                    inline_keyboard=kb.make_answer_button(), message_id=msg.message_id
                )
                await self.app.bus.postpone_publish(
                    events.WaitingPressTimeout(msg.update, msg.message_id),
                    msg.update.origin,
                    msg.update.chat_id,
                    delay=Delay.WAIT_PRESS
                )


class CatInBag(Handler):
    async def handler(self, msg: events.CatInBag):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_PRESS:
                return

            themes = await uow.themes.list()

            game.get_cat_from_bag(themes)

            await uow.commit()

            current_player = game.get_current_player()

            await self.app.bot(msg.update).edit(
                f"{current_player.link}, кому достанется кот в мешке?\n\n"
                f"{tools.players_rating(game.players)}"
                f"\n\n{texts.delay(Delay.WAIT_SELECTION)}",
                inline_keyboard=kb.make_players_menu(game.players),
                message_id=msg.message_id
            )

            await self.app.bus.postpone_publish(
                events.WaitingForCatCatcherTimeout(
                    msg.update, msg.message_id
                ),
                msg.update.origin, msg.update.chat_id, delay=Delay.WAIT_SELECTION
            )


class GiveCat(Handler):
    async def handler(self, msg: commands.GiveCat):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CAT_CATCHER:
                return

            player = game.give_cat(msg.user_id)

            await uow.commit()

            theme = await uow.themes.get(game.current_question.theme_id)

            current_player = game.get_current_player()

            await self.app.bot(msg.update).edit(
                f"{player.link}, {current_player.link} отдал кота в мешке вам!"
                f"\n\n«{theme.title} за {game.current_question.cost}»"
            )

            await self.app.bus.postpone_publish(
                commands.ShowQuestion(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.LITTLE_PAUSE
            )

            await self.app.bus.postpone_publish(
                commands.CatInBagAnswerPrompt(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.PAUSE
            )


class CatchCatTimeout(Handler):
    async def handler(self, msg: events.WaitingForCatCatcherTimeout):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CAT_CATCHER:
                return

            player = game.give_cat(choice(game.players).user_id)

            await uow.commit()

            theme = await uow.themes.get(game.current_question.theme_id)

            await self.app.bot(msg.update).edit(
                f"Время вышло!\n\n{player.link}, кот в мешке достался вам!"
                f"\n\n«{theme.title} за {game.current_question.cost}»",
                message_id=msg.message_id
            )

            await self.app.bus.postpone_publish(
                commands.ShowQuestion(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.LITTLE_PAUSE
            )

            await self.app.bus.postpone_publish(
                commands.CatInBagAnswerPrompt(msg.update),
                msg.update.origin, msg.update.chat_id,
                delay=Delay.PAUSE
            )


class CatInBagAnswerPrompt(Handler):
    async def handler(self, msg: commands.CatInBagAnswerPrompt):
        async with self.app.store.db() as uow:
            game = await uow.games.get(msg.update.origin, msg.update.chat_id)

            if not game or game.state != GameState.WAITING_FOR_CAT_CATCHER:
                return

            game.wait_answer_for_cat_in_bag()

            await uow.commit()

            player = game.get_answering_player()

            message_id = await self.app.bot(msg.update).send(
                f"{player.link}, кот ждёт ваш ответ:\n\n{texts.delay(tools.question_delay(game) + Delay.WAIT_ANSWER)}"
            )

            await self.app.bus.postpone_publish(
                events.WaitingForAnswerTimeout(msg.update, message_id),
                msg.update.origin, msg.update.chat_id,
                delay=tools.question_delay(game) + Delay.WAIT_ANSWER - Delay.PAUSE + Delay.LITTLE_PAUSE
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
        commands.ShowQuestion: [ShowQuestion],
        commands.PressButton: [PressButton],
        commands.Answer: [Answer],
        commands.PeekAnswer: [PeekAnswer],
        commands.RejectAnswer: [RejectAnswer],
        commands.AcceptAnswer: [AcceptAnswer],
        commands.VkRenderQuestions: [VkQuestionSelector],
        commands.TelegramRenderQuestions: [TelegramQuestionSelector],
        commands.HideQuestions: [HideQuestions],
        commands.ShowPress: [ShowPress],
        commands.GiveCat: [GiveCat],
        commands.CatInBagAnswerPrompt: [CatInBagAnswerPrompt],

        events.QuestionFinished: [NextSelection],
        events.GameFinished: [Results],
        events.WaitingForLeadingTimeout: [InitGameTimeout],
        events.RegistrationTimeout: [InitGameTimeout],
        events.WaitingSelectionTimeout: [SelectionTimeout],
        events.WaitingPressTimeout: [PressTimeout],
        events.WaitingForAnswerTimeout: [AnswerTimeout],
        events.WaitingForCheckingTimeout: [CheckingTimeout],
        events.CatInBag: [CatInBag],
        events.WaitingForCatCatcherTimeout: [CatchCatTimeout]
    })
