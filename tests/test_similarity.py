from flagquiz.flags import load_flags
from flagquiz.similarity import compute_hashes, distance, ranked_by_similarity


def test_distance_between_identical_image_is_zero():
    flags = load_flags()
    hashes = compute_hashes(flags)
    assert distance(hashes["jp"], hashes["jp"]) == 0


def test_similar_flags_are_closer_than_dissimilar_flags():
    # id (Indonesia: 赤白の横二色旗) と pl (Poland: 白赤の横二色旗) は構図が近く、
    # sa (Saudi Arabia: 緑地に文字と剣) とは構図が大きく異なる。
    flags = load_flags()
    hashes = compute_hashes(flags)
    assert distance(hashes["id"], hashes["pl"]) < distance(hashes["id"], hashes["sa"])


def test_ranked_by_similarity_excludes_self_and_covers_all_others():
    flags = load_flags()
    hashes = compute_hashes(flags)
    ranked = ranked_by_similarity("jp", hashes)
    assert "jp" not in ranked
    assert len(ranked) == len(flags) - 1
    assert set(ranked) == {f.code for f in flags if f.code != "jp"}
