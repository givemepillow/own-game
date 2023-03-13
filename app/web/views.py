from uuid import uuid4

from aiohttp_apispec import request_schema, response_schema, querystring_schema, form_schema
from sqlalchemy.exc import IntegrityError

from app.game.models import Theme
from app.utils.responses import json_response, error_json_response
from app.web.application import View
from app.web.schemas import NewThemeSchema, ThemeSchema, ResponseThemeSchema, DeleteParams, MediaForm, \
    DeleteMediaSchema, EditSchema, EditParams


class ThemeView(View):
    @request_schema(NewThemeSchema)
    async def post(self):
        try:
            async with self.app.store.db() as uow:
                uow.themes.add(Theme.from_dict(**self.data))
                await uow.commit()
            return json_response(message="New theme successfully added!")
        except IntegrityError:
            return error_json_response(http_status=409, message="Specific theme already exists!")

    @response_schema(ResponseThemeSchema)
    async def get(self):
        async with self.app.store.db() as uow:
            themes = await uow.themes.list()
            return json_response(data=[ThemeSchema().load(t.as_dict()) for t in themes])

    @request_schema(EditSchema)
    @querystring_schema(EditParams)
    async def patch(self):
        theme_id = int(self.request.rel_url.query.get('theme_id'))
        question_id = self.request.rel_url.query.get('question_id')

        title = self.data.get('title')
        question = self.data.get('question')
        answer = self.data.get('answer')

        async with self.app.store.db() as uow:
            theme = await uow.themes.get(theme_id)
            if not theme:
                return error_json_response(http_status=404, message="Specific theme not found!")
            if title:
                theme.title = title

            if question_id and (question or answer):
                question_id = int(question_id)
                for q in theme.questions:
                    if q.id == question_id:
                        if question:
                            q.question = question

                        if answer:
                            q.answer = answer

                        await uow.commit()
                        return json_response(message="Theme successfully updated!")
                return error_json_response(http_status=404, message="Specific question not found!")

            await uow.commit()
            return json_response(message="Theme successfully updated!")

    @querystring_schema(DeleteParams)
    async def delete(self):
        theme_id = int(self.request.rel_url.query['id'])
        async with self.app.store.db() as uow:
            theme = await uow.themes.get(theme_id)
            if not theme:
                return error_json_response(http_status=404, message="Specific theme not found!")
            for q in theme.questions:
                if q.filename is not None:
                    self.app.store.remove(q.filename)
            await uow.themes.delete(theme_id)
            await uow.commit()
        return json_response(message="Theme successfully deleted!")


class MediaView(View):
    @form_schema(MediaForm)
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
                        file = await field.read()
                        if q.filename:
                            self.app.store.remove(q.filename)
                        content_type = field.headers['Content-Type']
                        _, ext = content_type.split('/')
                        q.content_type = content_type
                        q.filename = str(uuid4().hex) + "." + ext
                        self.app.store.save(q.filename, file)
                        await uow.commit()
                        return json_response(message="Media successfully added!")
        return error_json_response(http_status=404, message="Specific question not found!")

    @request_schema(DeleteMediaSchema)
    async def delete(self):
        theme_id = int(self.request.match_info['theme_id'])
        question_id = int(self.request.match_info['question_id'])

        async with self.app.store.db() as uow:
            theme = await uow.themes.get(theme_id)
            if theme is None:
                return error_json_response(http_status=404, message="Specific theme not found!")
            for q in theme.questions:
                if q.id == question_id:
                    self.app.store.remove(q.filename)
                    q.filename = None
                    q.content_type = None
                    await uow.commit()
                    return json_response(message="Media successfully deleted!")
        return error_json_response(http_status=404, message="Specific question not found!")
