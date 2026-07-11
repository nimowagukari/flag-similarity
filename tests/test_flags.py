from flagquiz.flags import find_flag, get_flag, load_flags


def test_load_flags_returns_all_entries():
    flags = load_flags()
    assert len(flags) == 50


def test_no_duplicate_codes():
    flags = load_flags()
    codes = [flag.code for flag in flags]
    assert len(codes) == len(set(codes))


def test_every_flag_has_an_image_file():
    flags = load_flags()
    for flag in flags:
        assert flag.image_path.exists(), f"missing image for {flag.code}"


def test_get_flag_returns_matching_flag():
    flags = load_flags()
    jp = get_flag("jp", flags)
    assert jp.name_ja == "日本"
    assert jp.name_en == "Japan"


def test_get_flag_raises_for_unknown_code():
    flags = load_flags()
    try:
        get_flag("zz", flags)
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_find_flag_returns_none_for_unknown_code():
    flags = load_flags()
    assert find_flag("zz", flags) is None
    assert find_flag(None, flags) is None
