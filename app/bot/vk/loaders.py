from app.bot.updates import Origin
from app.bot.enums import ChatType, ActionType
from app.bot.inline import CallbackData
from app.bot.updates import BotCommand, BotAction, BotMessage, BotCallbackQuery


def define_chat_type(chat_id: int):
    return ChatType.GROUP if chat_id > 2000000000 else ChatType.PRIVATE


def update_from_dict(**data):
    match data:
        case {"object": {"message": {
            "from_id": user_id,
            "peer_id": peer_id
        }}}:
            return dict(
                origin=Origin.VK,
                user_id=user_id,
                chat_id=peer_id,
                chat_type=define_chat_type(peer_id),
                user=None
            )
        case {"object": {
            "user_id": user_id,
            "peer_id": peer_id,
        }}:
            return dict(
                origin=Origin.VK,
                user_id=user_id,
                chat_id=peer_id,
                chat_type=define_chat_type(peer_id),
                user=None
            )
    raise ValueError("Unprocessable VK update data.")


def command_from_dict(**data) -> BotCommand:
    match data:
        case {"object": {"message": {"text": text}}}:
            if text.startswith('/'):
                command, *_ = text.split()
                command = command.removeprefix('/')
            else:
                args = text.split(']')
                command = args[1].strip() if len(args) > 1 else ''
            return BotCommand(
                command=command,
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable VK command data.")


def action_from_dict(**data) -> BotAction:
    match data:
        case {"object": {"message": {"action": ({"type": _, "member_id": member_id})}}}:
            return BotAction(
                action=ActionType.ADD_TO_GROUP,
                target_id=member_id,
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable VK action data.")


def message_from_dict(**data) -> BotMessage:
    match data:
        case {"object": {"message": {"text": text}}}:
            return BotMessage(
                text=text,
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable VK message data.")


def callback_query_from_dict(**data) -> BotCallbackQuery:
    match data:
        case {"object": {
            "event_id": event_id,
            "payload": {"type": data_type, "value": value},
            "conversation_message_id": conversation_message_id
        }}:
            return BotCallbackQuery(
                message_id=conversation_message_id,
                callback_data=CallbackData(data_type, value),
                callback_query_id=event_id,
                **update_from_dict(**data)
            )
    raise ValueError("Unprocessable VK callback_query data.")
