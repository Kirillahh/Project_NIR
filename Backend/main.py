from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.orm import Session

import grading
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
    survey.is_published = data.is_published
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

#прохождение (публичное)

def load_published_survey(db: Session, survey_id: int) -> models.Survey:
    survey = db.get(models.Survey, survey_id)
    if survey is None or not survey.is_published:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    return survey


@app.get("/public/surveys/{survey_id}", response_model=schemas.PublicSurveyOut)
def get_public_survey(survey_id: int, db: Session = Depends(get_db)):
    return load_published_survey(db, survey_id)


@app.post(
    "/public/surveys/{survey_id}/submissions",
    response_model=schemas.SubmissionResultOut,
    status_code=201,
)
def submit_answers(survey_id: int, data: schemas.SubmissionCreate, db: Session = Depends(get_db)):
    survey = load_published_survey(db, survey_id)
    questions = {q.id: q for q in survey.questions}

    given = {}
    for a in data.answers:
        if a.question_id not in questions:
            raise HTTPException(status_code=422, detail=f"Вопрос {a.question_id} не относится к этому опросу")
        if a.question_id in given:
            raise HTTPException(status_code=422, detail=f"На вопрос {a.question_id} ответ отправлен дважды")
        given[a.question_id] = a

    submission = models.Submission(survey_id=survey.id, respondent_name=data.respondent_name)
    results = []
    total = 0.0
    max_total = 0.0

    for q in survey.questions:
        a = given.get(q.id)
        text = (a.text or "").strip() if a else ""
        selected_ids = set(a.selected_option_ids) if a else set()
        if q.type == "text":
            selected_ids = set()
        max_points = q.weight if survey.is_test else 0.0
        max_total += max_points
        answered = bool(text) if q.type == "text" else bool(selected_ids)

        if not answered:
            if q.is_required:
                raise HTTPException(status_code=422, detail=f"Нужно ответить на вопрос «{q.text}»")
            results.append(schemas.AnswerResultOut(question_id=q.id, points=0.0, max_points=max_points))
            continue

        if q.type != "text":
            valid_ids = {o.id for o in q.options}
            if not selected_ids <= valid_ids:
                raise HTTPException(status_code=422, detail=f"В вопросе «{q.text}» выбран неизвестный вариант")
            if q.type == "single" and len(selected_ids) > 1:
                raise HTTPException(status_code=422, detail=f"В вопросе «{q.text}» можно выбрать только один вариант")

        points = grading.grade_answer(q, selected_ids, text) if survey.is_test else 0.0
        answer = models.Answer(
            question_id=q.id,
            text_answer=text if q.type == "text" else None,
            points=points,
        )
        answer.selected_options = [o for o in q.options if o.id in selected_ids]
        submission.answers.append(answer)
        total += points
        results.append(schemas.AnswerResultOut(question_id=q.id, points=points, max_points=max_points))

    submission.score = round(total, 2)
    submission.max_score = max_total
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return schemas.SubmissionResultOut(
        submission_id=submission.id,
        is_test=survey.is_test,
        score=submission.score,
        max_score=submission.max_score,
        answers=results,
    )