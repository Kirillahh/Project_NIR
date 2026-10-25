import models


def grade_answer(question: models.Question, selected_ids: set[int], text: str) -> float:
    if question.type == "single":
        correct_ids = {o.id for o in question.options if o.is_correct}
        return question.weight if selected_ids == correct_ids else 0.0

    if question.type == "multiple":
        correct_ids = {o.id for o in question.options if o.is_correct}
        if not correct_ids:
            return 0.0
        right = len(selected_ids & correct_ids)
        wrong = len(selected_ids - correct_ids)
        share = max(0, right - wrong) / len(correct_ids)
        return round(question.weight * share, 2)

    if question.correct_text and text:
        same = text.strip().casefold() == question.correct_text.strip().casefold()
        return question.weight if same else 0.0

    return 0.0