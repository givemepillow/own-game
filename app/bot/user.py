from dataclasses import dataclass


@dataclass(slots=True)
class BotUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None

    @property
    def name(self):
        return f"{self.first_name}{(' ' + self.last_name) if self.last_name else ''}"

    @property
    def mention(self):
        return f"{self.name} @{self.username}" if self.username else self.name
