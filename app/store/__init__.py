from app.store.database import Database

from app.web.application import Application


class Store:
    def __init__(self, app: Application):
        self.db = Database(app)


def setup_store(app: Application):
    app['store'] = Store(app)
