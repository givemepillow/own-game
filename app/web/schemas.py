from marshmallow import fields, Schema, ValidationError, validates

from app.game.enums import QuestionComplexity


class NewQuestionSchema(Schema):
    id = fields.Int(required=False)
    question = fields.Str(required=True)
    complexity = fields.Enum(QuestionComplexity)
    answer = fields.Str(required=True)

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
    filename = fields.Str(allow_none=True, missing=None)
    content_type = fields.Str(allow_none=True, missing=None)


class ThemeSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    author = fields.Str()
    is_available = fields.Bool()
    created_at = fields.Str()
    questions = fields.List(fields.Nested(QuestionSchema()))


class ResponseThemeSchema(Schema):
    status = fields.Str()
    message = fields.Str()
    data = fields.List(fields.Nested(ThemeSchema()))


class DeleteParams(Schema):
    id = fields.Int(required=True)


class MediaForm(Schema):
    pass


class DeleteMediaSchema(Schema):
    pass
