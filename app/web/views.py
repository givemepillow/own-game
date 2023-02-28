from aiohttp_apispec import request_schema

from app.game.models import Theme
from app.utils.responses import json_response
from app.web.application import View
from app.web.schemas import NewThemeSchema


class ThemeView(View):
    @request_schema(NewThemeSchema)
    async def post(self):
        async with self.app.store.db() as uow:
            uow.themes.add(Theme.from_dict(**self.data))
            await uow.commit()
        return json_response(message="New theme successfully added!")
