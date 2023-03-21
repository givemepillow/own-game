from app.game.models import Player

NUMBERS = {
    '0': '0️⃣',
    '1': '1️⃣',
    '2': '2️⃣',
    '3': '3️⃣',
    '4': '4️⃣',
    '5': '5️⃣',
    '6': '6️⃣',
    '7': '7️⃣',
    '8': '8️⃣',
    '9': '9️⃣'
}


def players_list(players: list[Player]) -> str:
    rows = [f"Регистрация. Игроков зарегистрировано: {len(players)}." + ('\n' if players else '')]
    for i, player in enumerate(players, start=1):
        rows.append(f"{i}. {player.link}")
    return '\n'.join(rows)


def players_rating(players: list[Player]) -> str:
    rows = []

    def medals():
        for m in '🥇🥈🥉':
            yield m
        while True:
            yield '🎗'

    players = sorted(players, reverse=True, key=lambda player: player.points)
    for p, medal in zip(players, medals()):
        rows.append(f"{medal} {p.link}: {p.points} очков")
    return '\n'.join(rows)


def convert_number(points: int):
    return ''.join((NUMBERS[p] for p in str(points)))
