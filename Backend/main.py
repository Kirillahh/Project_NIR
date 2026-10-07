from fastapi import FastAPI

app = FastAPI(title="Survey App")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/hello/{name}")
def hello(name: str):
    return {"message": f"Привет, {name}!"}


@app.get("/surveys/{survey_id}")
def get_survey(survey_id: int):
    return {"id": survey_id, "title": "Тестовый опрос"}