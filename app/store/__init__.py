import os
from pathlib import Path

from app.web.application import Application


class Store:
    def __init__(self, app: Application):
        self._dir = app.config.settings.media_dir

        from app.store.database import Database
        self.db = Database(app)

    def save(self, name: str, file: bytes):
        with open(f"{self._dir}/{name}", 'wb') as f:
            f.write(file)

    def remove(self, name: str):
        os.remove(f"{self._dir}/{name}")

    def path(self, name: str) -> str:
        return f"{self._dir}/{name}"


def setup_store(app: Application):
    from app.store.bus import MessageBus

    app['store'] = Store(app)
    app['bus'] = MessageBus(app)
