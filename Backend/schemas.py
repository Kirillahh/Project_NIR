from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


#то, что присылает клиент

class OptionCreate(BaseModel):
    text: str
    is_correct: bool = False


class QuestionCreate(BaseModel):
    text: str
    type: Literal["single", "multiple", "text"]
    weight: float = 1.0
    is_required: bool = False
    correct_text: Optional[str] = None
    options: list[OptionCreate] = []


class SurveyCreate(BaseModel):
    title: str
    description: str = ""
    is_test: bool = False
    questions: list[QuestionCreate] = []

    @model_validator(mode="after")
    def check_questions(self):
        for q in self.questions:
            if q.type == "text":
                if q.options:
                    raise ValueError(f"У текстового вопроса «{q.text}» не должно быть вариантов")
            else:
                if len(q.options) < 2:
                    raise ValueError(f"В вопросе «{q.text}» нужно минимум 2 варианта")
                if self.is_test:
                    correct = sum(o.is_correct for o in q.options)
                    if q.type == "single" and correct != 1:
                        raise ValueError(f"В вопросе «{q.text}» должен быть ровно один правильный вариант")
                    if q.type == "multiple" and correct < 1:
                        raise ValueError(f"В вопросе «{q.text}» нужен хотя бы один правильный вариант")
        return self


class SurveyUpdate(BaseModel):
    title: str
    description: str = ""
    is_test: bool = False
    is_published: bool = False


#то, что отвечает сервер

class OptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    is_correct: bool
    position: int


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    type: str
    weight: float
    is_required: bool
    correct_text: Optional[str]
    position: int
    options: list[OptionOut]


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    is_test: bool
    is_published: bool
    created_at: datetime


class SurveyDetailOut(SurveyOut):
    questions: list[QuestionOut]

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
    
class TokenOut(BaseModel):
    access_token:str
    token_type: str

class PublicOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    position: int


class PublicQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    type: str
    weight: float
    is_required: bool
    position: int
    options: list[PublicOptionOut]


class PublicSurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    is_test: bool
    questions: list[PublicQuestionOut]


class AnswerIn(BaseModel):
    question_id: int
    selected_option_ids: list[int] = []
    text: Optional[str] = Field(default=None, max_length=2000)


class SubmissionCreate(BaseModel):
    respondent_name: Optional[str] = Field(default=None, max_length=100)
    answers: list[AnswerIn] = []


class AnswerResultOut(BaseModel):
    question_id: int
    points: float
    max_points: float


class SubmissionResultOut(BaseModel):
    submission_id: int
    is_test: bool
    score: float
    max_score: float
    answers: list[AnswerResultOut]

