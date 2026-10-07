from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Survey App")


class SurveyCreate(BaseModel):
    title: str
    description: str = ""
    is_test: bool = False


surveys = []   # временное хранилище
next_id = 1    # счётчик для id


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/surveys", status_code=201)
def create_survey(data: SurveyCreate):
    global next_id
    survey = {"id": next_id, **data.model_dump()}
    surveys.append(survey)
    next_id += 1
    return survey


@app.get("/surveys")
def list_surveys():
    return surveys


@app.get("/surveys/{survey_id}")
def get_survey(survey_id: int):
    for survey in surveys:
        if survey["id"] == survey_id:
            return survey
    raise HTTPException(status_code=404, detail="Опрос не найден")


@app.delete("/surveys/{survey_id}")
def delete_survey(survey_id: int):
    for survey in surveys:
        if survey["id"] == survey_id:
            surveys.remove(survey)
            return {"deleted": survey_id}
    raise HTTPException(status_code=404, detail="Опрос не найден")