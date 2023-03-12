from app.game.enums import Delay


def delay(seconds: Delay) -> str:
    return f"⏱ {seconds} сек."
