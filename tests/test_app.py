import pytest

from app import FERNET, app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_returns_200_and_four_choices(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.data.count(b'name="choice"') == 4


def test_answer_with_correct_choice_shows_correct_message(client):
    client.get("/")
    with client.session_transaction() as sess:
        correct_code = FERNET.decrypt(sess["correct_token"].encode()).decode()

    resp = client.post("/answer", data={"choice": correct_code})
    assert resp.status_code == 200
    assert "正解！".encode() in resp.data


def test_answer_with_wrong_choice_shows_incorrect_message(client):
    client.get("/")
    with client.session_transaction() as sess:
        correct_code = FERNET.decrypt(sess["correct_token"].encode()).decode()

    wrong_code = "jp" if correct_code != "jp" else "us"
    resp = client.post("/answer", data={"choice": wrong_code})
    assert resp.status_code == 200
    assert "不正解".encode() in resp.data


def test_answer_with_unknown_choice_code_is_treated_as_incorrect(client):
    client.get("/")
    resp = client.post("/answer", data={"choice": "not-a-real-code"})
    assert resp.status_code == 200
    assert "不正解".encode() in resp.data


def test_session_cookie_does_not_expose_plaintext_answer(client):
    resp = client.get("/")
    with client.session_transaction() as sess:
        correct_code = FERNET.decrypt(sess["correct_token"].encode()).decode()

    set_cookie = resp.headers.get("Set-Cookie", "")
    assert correct_code not in set_cookie
    assert "correct_code" not in set_cookie
