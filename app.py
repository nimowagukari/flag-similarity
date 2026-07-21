import json
import logging
import os
import time

from cryptography.fernet import InvalidToken
from flask import Flask, abort, g, render_template, request, session

from flagquiz.crypto import build_fernet
from flagquiz.flags import find_flag, get_flag, load_flags
from flagquiz.question import DIFFICULTY_BANDS, generate_question
from flagquiz.similarity import compute_hashes

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
FERNET = build_fernet(app.secret_key)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FLAGS = load_flags()
HASHES = compute_hashes(FLAGS)

DEFAULT_DIFFICULTY = "normal"


@app.before_request
def _start_timer():
    g.start_time = time.perf_counter()


@app.after_request
def _log_request(response):
    duration_ms = (time.perf_counter() - g.start_time) * 1000
    logger.info(
        json.dumps(
            {
                "path": request.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            }
        )
    )
    return response


def _resolve_difficulty(value: str | None) -> str:
    if value in DIFFICULTY_BANDS:
        return value
    return DEFAULT_DIFFICULTY


@app.route("/")
def index():
    difficulty = _resolve_difficulty(request.args.get("difficulty"))
    question = generate_question(FLAGS, HASHES, difficulty=difficulty)

    session["correct_token"] = FERNET.encrypt(question.correct_code.encode()).decode()
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
    correct_token = session.get("correct_token")
    difficulty = session.get("difficulty", DEFAULT_DIFFICULTY)
    if correct_token is None:
        abort(400)

    try:
        correct_code = FERNET.decrypt(correct_token.encode()).decode()
    except InvalidToken:
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
