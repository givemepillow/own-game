from uuid import uuid4

from aiohttp_apispec import request_schema, response_schema

from app.game.models import Theme
from app.utils.responses import json_response, error_json_response
from app.web.application import View
from app.web.schemas import NewThemeSchema, ThemeSchema, ResponseThemeSchema


class ThemeView(View):
    @request_schema(NewThemeSchema)
    async def post(self):
        async with self.app.store.db() as uow:
            uow.themes.add(Theme.from_dict(**self.data))
            await uow.commit()
        return json_response(message="New theme successfully added!")

    @response_schema(ResponseThemeSchema)
    async def get(self):
        async with self.app.store.db() as uow:
            themes = await uow.themes.list()
            return json_response(data=[ThemeSchema().load(t.as_dict()) for t in themes])


class MediaView(View):
    async def put(self):
        theme_id = int(self.request.match_info['theme_id'])
        question_id = int(self.request.match_info['question_id'])

        async with self.app.store.db() as uow:
            theme = await uow.themes.get(theme_id)
            if theme is None:
                return error_json_response(http_status=404, message="Specific theme not found!")
            for q in theme.questions:
                if q.id == question_id:
                    async for field in (await self.request.multipart()):
                        content_type = field.headers['Content-Type']
                        _, ext = content_type.split('/')
                        q.content_type = content_type
                        q.filename = str(uuid4().hex) + "." + ext
                        self.app.store.save(q.filename, await field.read())
                        await uow.commit()
                        return json_response(message="Media successfully added!")
        return error_json_response(http_status=404, message="Specific question not found!")
