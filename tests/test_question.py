from flagquiz.flags import load_flags
from flagquiz.question import generate_question
from flagquiz.similarity import compute_hashes, distance


def test_generate_question_has_four_unique_choices_including_correct():
    flags = load_flags()
    hashes = compute_hashes(flags)
    for difficulty in ("hard", "normal", "easy"):
        question = generate_question(flags, hashes, difficulty=difficulty)
        assert len(question.choices) == 4
        assert len(set(question.choices)) == 4
        assert question.correct_code in question.choices


def test_hard_dummies_are_closer_on_average_than_easy_dummies():
    flags = load_flags()
    hashes = compute_hashes(flags)

    def avg_dummy_distance(difficulty, trials=30):
        total = 0
        for _ in range(trials):
            question = generate_question(flags, hashes, difficulty=difficulty)
            dummy_codes = [c for c in question.choices if c != question.correct_code]
            total += sum(distance(hashes[question.correct_code], hashes[c]) for c in dummy_codes)
        return total / trials

    assert avg_dummy_distance("hard") < avg_dummy_distance("easy")
