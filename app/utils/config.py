import os
from dataclasses import dataclass, field

import yaml

from app.web.application import Application


@dataclass
class SettingsConfig:
    debug: bool = field(default_factory=bool)


@dataclass
class SessionConfig:
    key: str


@dataclass
class AdminConfig:
    email: str
    password: str


@dataclass
class DatabaseConfig:
    engine: str
    driver: str
    user: str
    password: str
    database: str
    host: str
    port: int

    @property
    def dsn(self) -> str:
        return ''.join([
            f'{self.engine}+{self.driver}://',
            f'{self.user or ""}:{self.password or ""}@',
            f'{self.host or ""}:{self.port or 0}/',
            f'{self.database + (".db" if self.engine == "sqlite" else "")}'
        ])


@dataclass
class Config:
    session: SessionConfig
    database: DatabaseConfig
    admin: AdminConfig
    settings: SettingsConfig

    @classmethod
    def load(cls):
        with open(os.environ.get('CONFIG_PATH') or "config.yml", "r") as f:
            raw_config = yaml.safe_load(f)
        return cls(
            settings=SettingsConfig(**raw_config["settings"]),
            session=SessionConfig(**raw_config["session"]),
            database=DatabaseConfig(**raw_config["database"]),
            admin=AdminConfig(**raw_config["admin"])
        )


def setup_config(app: "Application"):
    app['config'] = Config.load()
