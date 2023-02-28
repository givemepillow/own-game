from marshmallow import fields, Schema, ValidationError, validates

from app.game.enums import QuestionComplexity


class NewAnswerSchema(Schema):
    answer = fields.Str(required=True)


class NewQuestionSchema(Schema):
    id = fields.Int(required=False)
    question = fields.Str(required=True)
    complexity = fields.Enum(QuestionComplexity)
    answers = fields.List(fields.Nested(NewAnswerSchema(), required=True))

    @validates("answers")
    def validate_answers(self, answers: list[dict]):
        if len(answers) < 1:
            raise ValidationError("number of answers must be more than zero")


class NewThemeSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)
    author = fields.Str(default='Без автора.', required=True)
    questions = fields.List(fields.Nested(NewQuestionSchema(), required=True))
