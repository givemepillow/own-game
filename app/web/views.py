from uuid import uuid4

from aiohttp.web_exceptions import HTTPUnauthorized
from aiohttp_apispec import request_schema, response_schema, docs
from aiohttp_session import new_session, get_session
from sqlalchemy.exc import IntegrityError

from app.admin.models import SessionAdmin
from app.game.models import Theme
from app.utils.responses import json_response, error_json_response
from app.web.application import View, AuthRequired
from app.web.schemas import NewThemeSchema, ThemeSchema, ResponseThemesSchema, EditThemeSchema, EditQuestionSchema, \
    ResponseThemeSchema, LoginAdminSchema, AdminSchema


class SessionView(View):
    @docs(tags=["session"])
    @request_schema(LoginAdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        async with self.app.store.db() as uow:
            admin = await uow.admins.get(self.data['email'])
            if admin and admin.is_password_valid(self.data['password']):
                verified_admin = AdminSchema().dump(admin)
                session = await new_session(self.request)
                session['admin'] = verified_admin
                return json_response(data=verified_admin)
        return error_json_response(message="invalid email or password", http_status=403)

    @docs(tags=["session"])
    @response_schema(AdminSchema, 200)
    async def get(self):
        session = await get_session(self.request)
        if not session:
            raise HTTPUnauthorized
        admin = SessionAdmin(**(session['admin']))
        return json_response(data=AdminSchema().dump(admin))


@AuthRequired
class ThemesView(View):
    @docs(tags=["themes"])
    @request_schema(NewThemeSchema)
    async def post(self):
        try:
            async with self.app.store.db() as uow:
                uow.themes.add(Theme.from_dict(**self.data))
                await uow.commit()
            return json_response(message="New theme successfully added!")
        except IntegrityError:
            return error_json_response(http_status=409, message="Specific theme already exists!")

    @docs(tags=["themes"])
    @response_schema(ResponseThemesSchema)
    async def get(self):
        async with self.app.store.db() as uow:
            themes = await uow.themes.list()
            return json_response(data=[ThemeSchema().load(t.as_dict()) for t in themes])


@AuthRequired
class MediaView(View):
    @docs(tags=["media"])
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

    @docs(tags=["media"])
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


@AuthRequired
class ThemeView(View):
    @docs(tags=["theme"])
    @response_schema(ResponseThemeSchema)
    async def get(self):
        theme_id = int(self.request.match_info['theme_id'])
        async with self.app.store.db() as uow:
            theme = await uow.themes.get()
            return json_response(data=ThemeSchema().load(theme.as_dict()))

    @docs(tags=["theme"])
    @request_schema(EditThemeSchema)
    async def patch(self):
        theme_id = int(self.request.match_info['theme_id'])

        title = self.data.get('title')

        async with self.app.store.db() as uow:
            theme = await uow.themes.get(theme_id)
            if not theme:
                return error_json_response(http_status=404, message="Specific theme not found!")
            if title:
                theme.title = title

            await uow.commit()
            return json_response(message="Theme successfully updated!")

    @docs(tags=["theme"])
    async def delete(self):
        theme_id = int(self.request.match_info['theme_id'])

        async with self.app.store.db() as uow:
            theme = await uow.themes.get()
            if not theme:
                return error_json_response(http_status=404, message="Specific theme not found!")
            for q in theme.questions:
                if q.filename is not None:
                    self.app.store.remove(q.filename)
            await uow.themes.delete(theme_id)
            await uow.commit()
        return json_response(message="Theme successfully deleted!")


@AuthRequired
class QuestionView(View):
    @docs(tags=["question"])
    @request_schema(EditQuestionSchema)
    async def patch(self):
        theme_id = int(self.request.match_info['theme_id'])
        question_id = int(self.request.match_info['question_id'])

        question = self.data.get('question')
        answer = self.data.get('answer')
        duration = self.data.get('duration')

        async with self.app.store.db() as uow:
            theme = await uow.themes.get(theme_id)
            if not theme:
                return error_json_response(http_status=404, message="Specific theme not found!")

            if question_id and (question or answer or duration):
                question_id = int(question_id)
                for q in theme.questions:
                    if q.id == question_id:
                        if question:
                            q.question = question

                        if answer:
                            q.answer = answer

                        if duration:
                            q.duration = duration

                        await uow.commit()
                        return json_response(message="Theme successfully updated!")

            return error_json_response(http_status=404, message="Specific question not found!")
