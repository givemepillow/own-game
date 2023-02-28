from dataclasses import dataclass, field
from typing import Iterable, Final

PLUG: Final = '_'


@dataclass(slots=True)
class CallbackData:
    type: str = PLUG
    value: str = PLUG


@dataclass(slots=True)
class InlineButton:
    text: str = ' '
    callback_data: CallbackData = field(default_factory=CallbackData)


class InlineKeyboard:
    def __init__(self):
        self._keyboard = []

    def __iter__(self) -> Iterable[tuple[InlineButton]]:
        return iter(self._keyboard)

    def add(self, *buttons: InlineButton):
        self._keyboard.append(buttons)
