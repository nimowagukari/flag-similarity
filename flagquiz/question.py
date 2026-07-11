import random
from dataclasses import dataclass

import imagehash

from flagquiz.flags import Flag
from flagquiz.similarity import ranked_by_similarity

# 類似度の順位帯（0-indexedのランク範囲）。国数が少ないため常に3件以上の候補を確保できる。
DIFFICULTY_BANDS = {
    "hard": (0, 3),
    "normal": (3, 15),
    "easy": (15, None),
}


@dataclass(frozen=True)
class Question:
    correct_code: str
    choices: list[str]
    difficulty: str


def select_dummy_codes(ranked: list[str], difficulty: str) -> list[str]:
    start, end = DIFFICULTY_BANDS[difficulty]
    band = ranked[start:end]
    return random.sample(band, 3)


def generate_question(
    flags: list[Flag], hashes: dict[str, imagehash.ImageHash], difficulty: str = "normal"
) -> Question:
    correct = random.choice(flags)
    ranked = ranked_by_similarity(correct.code, hashes)
    dummy_codes = select_dummy_codes(ranked, difficulty)
    choices = [correct.code, *dummy_codes]
    random.shuffle(choices)
    return Question(correct_code=correct.code, choices=choices, difficulty=difficulty)
