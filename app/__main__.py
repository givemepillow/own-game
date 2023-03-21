from app.web.bootstrap import app_factory
from aiohttp import web

if __name__ == "__main__":
    web.run_app(app_factory())
