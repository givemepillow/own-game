from app.game.models import Player


def players_list(players: list[Player]) -> str:
    rows = [f"Регистрация. Игроков зарегистрировано: {len(players)}."]
    for i, player in enumerate(players, start=1):
        rows.append(f"{i}. {player.name}")
    return '\n'.join(rows)


def players_rating(players: list[Player]) -> str:
    rows = []
    players = sorted(players, reverse=True, key=lambda player: player.points)
    for p in players:
        rows.append(f"{p.name}: {p.points} очков")
    return '\n'.join(rows)
