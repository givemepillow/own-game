import logging

from app.web.application import Application


def setup_logging(app: Application) -> None:
    logging.basicConfig(
        level=logging.DEBUG if app.config.settings.debug else logging.INFO
    )
