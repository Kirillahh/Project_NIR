from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SurveyCreate(BaseModel):
    title: str
    description: str = ""
    is_test: bool = False


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    is_test: bool
    is_published: bool
    created_at: datetime