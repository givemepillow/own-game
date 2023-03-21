from orjson import orjson

from app.bot.updates import Origin
from app.bot.enums import ChatType, ActionType
from app.bot.inline import CallbackData
from app.bot.updates import BotCommand, BotAction, BotMessage, BotCallbackQuery
from app.bot.user import BotUser


def update_from_dict(**data):
    match data:
        case {"message": {
            "from": {"id": user_id} as from_,
            "chat": {"id": chat_id, "type": chat_type}
        }}:
            return dict(
                origin=Origin.TELEGRAM,
                user_id=user_id,
                chat_id=chat_id,
                chat_type=ChatType.PRIVATE if chat_type == 'private' else ChatType.GROUP,
                user=BotUser(
                    id=user_id,
                    first_name=from_.get('first_name'),
                    last_name=from_.get('last_name'),
                    username=from_.get('username')
                )
            )
        case {"callback_query": {
            "from": {"id": user_id} as from_,
            "message": {"chat": {"id": chat_id, "type": chat_type}}
        }}:
            return dict(
                origin=Origin.TELEGRAM,
                user_id=user_id,
                chat_id=chat_id,
                chat_type=ChatType.PRIVATE if chat_type == 'private' else ChatType.GROUP,
                user=BotUser(
                    id=user_id,
                    first_name=from_.get('first_name'),
                    last_name=from_.get('last_name'),
                    username=from_.get('username')
                )
            )
    raise ValueError("Unprocessable update data.")


def command_from_dict(**data) -> BotCommand:
    match data:
        case {"message": {"text": text}}:
            command, *_ = text.split()
            return BotCommand(
                command=command.removeprefix('/'),
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable Telegram command.")


def action_from_dict(**data) -> BotAction:
    match data:
        case {"message": {"new_chat_member": {"id": target_id}}}:
            return BotAction(
                action=ActionType.ADD_TO_GROUP,
                target_id=target_id,
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable Telegram action data.")


def message_from_dict(**data) -> BotMessage:
    match data:
        case {"message": {"text": text}}:
            return BotMessage(text=text, **update_from_dict(**data))
    raise ValueError("Unprocessable Telegram message data/")


def callback_query_from_dict(**data) -> BotCallbackQuery:
    match data:
        case {"callback_query": {
            "id": callback_query_id,
            "data": callback_data,
            "message": {"message_id": message_id}
        }}:
            return BotCallbackQuery(
                callback_data=CallbackData(**orjson.loads(callback_data)),
                message_id=message_id,
                callback_query_id=callback_query_id,
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable Telegram callback_query data/")
