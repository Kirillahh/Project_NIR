from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from pwdlib import PasswordHash

app = FastAPI(title="Survey App")

password_hasher = PasswordHash.recommended()

TEMP_OWNER_ID = 1  # временно, пока нет авторизации


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/surveys", response_model=schemas.SurveyDetailOut, status_code=201)
def create_survey(data: schemas.SurveyCreate, db: Session = Depends(get_db)):
    survey = models.Survey(
        owner_id=TEMP_OWNER_ID,
        title=data.title,
        description=data.description,
        is_test=data.is_test,
    )
    for q_pos, q in enumerate(data.questions, start=1):
        question = models.Question(
            text=q.text,
            type=q.type,
            weight=q.weight,
            is_required=q.is_required,
            correct_text=q.correct_text,
            position=q_pos,
        )
        for o_pos, o in enumerate(q.options, start=1):
            question.options.append(
                models.Option(text=o.text, is_correct=o.is_correct, position=o_pos)
            )
        survey.questions.append(question)

    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@app.get("/surveys", response_model=list[schemas.SurveyOut])
def list_surveys(db: Session = Depends(get_db)):
    return db.scalars(select(models.Survey)).all()


@app.get("/surveys/{survey_id}", response_model=schemas.SurveyDetailOut)
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
def update_survey(survey_id: int, data: schemas.SurveyUpdate, db: Session = Depends(get_db)):
    survey=db.get(models.Survey, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    survey.title =data.title
    survey.description=data.description
    survey.is_test=data.is_test
    db.commit()
    db.refresh(survey)
    return survey

@app.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    question = db.get(models.Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    db.delete(question)
    db.commit()
    return {"deleted": question_id}

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()
    existing = db.scalar(select(models.User).where(models.User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Пользователь с такой почтой уже есть")
    user = models.User(email=email, password_hash=password_hasher.hash(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user