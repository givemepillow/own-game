from marshmallow import fields, Schema, ValidationError, validates

from app.game.enums import QuestionComplexity


class NewAnswerSchema(Schema):
    answer = fields.Str(required=True)


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
