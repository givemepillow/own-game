from marshmallow import fields, Schema, ValidationError, validates

from app.game.enums import QuestionComplexity


class NewQuestionSchema(Schema):
    id = fields.Int(required=False)
    question = fields.Str(required=True)
    complexity = fields.Enum(QuestionComplexity)
    answer = fields.Str(required=True)
    duration = fields.Int(required=True)

    @validates("answer")
    def validate_answer(self, answers: list[dict]):
        if not (90 > len(answers) > 1):
            raise ValidationError("answer length should be between 1 and 90")


class NewThemeSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)
    author = fields.Str(default='Без автора.', required=True)
    questions = fields.List(fields.Nested(NewQuestionSchema(), required=True))


class MediaFileSchema(Schema):
    id = fields.Int()
    question = fields.Str()
    cost = fields.Int()
    answer = fields.Str()


class QuestionSchema(Schema):
    id = fields.Int()
    question = fields.Str()
    cost = fields.Int()
    answer = fields.Str()
    duration = fields.Int()
    filename = fields.Str(allow_none=True, missing=None)
    content_type = fields.Str(allow_none=True, missing=None)


class ThemeSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    author = fields.Str()
    is_available = fields.Bool()
    created_at = fields.Str()
    questions = fields.List(fields.Nested(QuestionSchema()))


class ResponseThemesSchema(Schema):
    status = fields.Str()
    message = fields.Str()
    data = fields.List(fields.Nested(ThemeSchema()))


class ResponseThemeSchema(Schema):
    status = fields.Str()
    message = fields.Str()
    data = fields.Nested(ThemeSchema())


class EditQuestionSchema(Schema):
    question = fields.Str(required=False, allow_none=True, missing=None)
    answer = fields.Str(required=False, allow_none=True, missing=None)
    duration = fields.Int(required=False, allow_none=True, missing=None)

    @validates("duration")
    def validate_answer(self, duration: int | None):
        if duration is not None and not (60 >= duration >= 5):
            raise ValidationError("question duration should be between 5 and 60")


class EditThemeSchema(Schema):
    title = fields.Str(required=True)
