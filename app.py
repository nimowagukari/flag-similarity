import os

from flask import Flask, abort, render_template, request, session

from flagquiz.flags import find_flag, get_flag, load_flags
from flagquiz.question import DIFFICULTY_BANDS, generate_question
from flagquiz.similarity import compute_hashes

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

FLAGS = load_flags()
HASHES = compute_hashes(FLAGS)

DEFAULT_DIFFICULTY = "normal"


def _resolve_difficulty(value: str | None) -> str:
    if value in DIFFICULTY_BANDS:
        return value
    return DEFAULT_DIFFICULTY


@app.route("/")
def index():
    difficulty = _resolve_difficulty(request.args.get("difficulty"))
    question = generate_question(FLAGS, HASHES, difficulty=difficulty)

    session["correct_code"] = question.correct_code
    session["difficulty"] = question.difficulty

    correct_flag = get_flag(question.correct_code, FLAGS)
    choice_flags = [get_flag(code, FLAGS) for code in question.choices]

    return render_template(
        "quiz.html",
        correct_flag=correct_flag,
        choice_flags=choice_flags,
        difficulty=question.difficulty,
        difficulties=list(DIFFICULTY_BANDS),
    )


@app.route("/answer", methods=["POST"])
def answer():
    correct_code = session.get("correct_code")
    difficulty = session.get("difficulty", DEFAULT_DIFFICULTY)
    if correct_code is None:
        abort(400)

    selected_code = request.form.get("choice")

    correct_flag = get_flag(correct_code, FLAGS)
    selected_flag = find_flag(selected_code, FLAGS)
    is_correct = selected_flag is not None and selected_code == correct_code

    return render_template(
        "result.html",
        is_correct=is_correct,
        correct_flag=correct_flag,
        selected_flag=selected_flag,
        difficulty=difficulty,
    )


if __name__ == "__main__":
    app.run(debug=True)
