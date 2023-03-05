from enum import StrEnum, auto


class Origin(StrEnum):
    VK: str = auto()
    TELEGRAM: str = auto()


class ChatType(StrEnum):
    PRIVATE: str = auto()
    GROUP: str = auto()


class ActionType(StrEnum):
    ADD_TO_GROUP: str = auto()
