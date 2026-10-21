from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import create_access_token, get_current_user, password_hasher

app = FastAPI(title="Survey App")


def get_own_survey(db: Session, survey_id: int, user: models.User) -> models.Survey:
    survey = db.get(models.Survey, survey_id)
    if survey is None or survey.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    return survey


@app.get("/health")
def health():
    return {"status": "ok"}


#авторизация

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


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == form.username.lower()))
    password_ok = False
    if user is not None:
        try:
            password_ok = password_hasher.verify(form.password, user.password_hash)
        except UnknownHashError:
            password_ok = False
    if not password_ok:
        raise HTTPException(
            status_code=401,
            detail="Неверная почта или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


#опросы

@app.post("/surveys", response_model=schemas.SurveyDetailOut, status_code=201)
def create_survey(
    data: schemas.SurveyCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    survey = models.Survey(
        owner_id=user.id,
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
def list_surveys(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = select(models.Survey).where(models.Survey.owner_id == user.id).order_by(models.Survey.id)
    return db.scalars(query).all()


@app.get("/surveys/{survey_id}", response_model=schemas.SurveyDetailOut)
def get_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return get_own_survey(db, survey_id, user)


@app.put("/surveys/{survey_id}", response_model=schemas.SurveyOut)
def update_survey(
    survey_id: int,
    data: schemas.SurveyUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    survey = get_own_survey(db, survey_id, user)
    survey.title = data.title
    survey.description = data.description
    survey.is_test = data.is_test
    db.commit()
    db.refresh(survey)
    return survey


@app.delete("/surveys/{survey_id}")
def delete_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    survey = get_own_survey(db, survey_id, user)
    db.delete(survey)
    db.commit()
    return {"deleted": survey_id}


#вопросы

@app.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    question = db.get(models.Question, question_id)
    if question is None or question.survey.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    db.delete(question)
    db.commit()
    return {"deleted": question_id}