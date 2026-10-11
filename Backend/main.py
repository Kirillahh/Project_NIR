from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

app = FastAPI(title="Survey App")

TEMP_OWNER_ID = 1  # временно, пока нет авторизации


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/surveys", response_model=schemas.SurveyOut, status_code=201)
def create_survey(data: schemas.SurveyCreate, db: Session = Depends(get_db)):
    survey = models.Survey(owner_id=TEMP_OWNER_ID, **data.model_dump())
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@app.get("/surveys", response_model=list[schemas.SurveyOut])
def list_surveys(db: Session = Depends(get_db)):
    return db.scalars(select(models.Survey)).all()


@app.get("/surveys/{survey_id}", response_model=schemas.SurveyOut)
def get_survey(survey_id: int, db: Session = Depends(get_db)):
    survey = db.get(models.Survey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    return survey


@app.delete("/surveys/{survey_id}")
def delete_survey(survey_id: int, db: Session = Depends(get_db)):
    survey = db.get(models.Survey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    db.delete(survey)
    db.commit()
    return {"deleted": survey_id}

@app.put("/surveys/{survey_id}", response_model=schemas.SurveyOut)
def update_survey(survey_id: int, data: schemas.SurveyCreate, db: Session = Depends(get_db)):
    survey=db.get(models.Survey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    survey.title =data.title
    survey.description=data.description
    survey.is_test=data.is_test
    db.commit()
    db.refresh(survey)
    return survey
