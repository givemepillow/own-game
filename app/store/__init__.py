from app.web.application import Application


class Store:
    def __init__(self, app: Application):
        from app.store.database import Database
        self.db = Database(app)


def setup_store(app: Application):
    from app.store.bus import MessageBus

    app['store'] = Store(app)
    app['bus'] = MessageBus(app)
