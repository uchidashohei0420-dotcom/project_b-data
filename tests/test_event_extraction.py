"""Direct tests for the shared date/time/location regex extraction (event_extraction.py),
independent of either source that calls it."""
from collector.event_extraction import extract_event_datetime, extract_location


def test_extracts_datetime_when_both_date_and_time_present():
    assert (
        extract_event_datetime("9月15日18時30分よりトークイベント開催", reference_year=2026)
        == "2026-09-15T18:30:00+09:00"
    )


def test_extracts_datetime_with_colon_time_format():
    assert (
        extract_event_datetime("9月15日 18:30 開場", reference_year=2026)
        == "2026-09-15T18:30:00+09:00"
    )


def test_returns_none_when_date_present_but_no_time():
    # A date with no time is left unset rather than defaulted to 00:00 — that would invent
    # information the source never actually stated.
    assert extract_event_datetime("9月15日にトークイベント開催", reference_year=2026) is None


def test_returns_none_when_time_present_but_no_date():
    assert extract_event_datetime("18時30分よりトークイベント開催", reference_year=2026) is None


def test_returns_none_for_impossible_date():
    assert extract_event_datetime("13月45日25時00分開催", reference_year=2026) is None


def test_returns_none_when_neither_date_nor_time_present():
    assert extract_event_datetime("トークイベント開催決定！詳細は近日公開", reference_year=2026) is None


def test_extracts_datetime_with_slash_date_format():
    assert (
        extract_event_datetime("8/21 18時30分よりトークイベント開催", reference_year=2026)
        == "2026-08-21T18:30:00+09:00"
    )


def test_extracts_datetime_with_slash_date_surrounded_by_decoration():
    assert (
        extract_event_datetime("帰ってきた！あたしンちフェア〜8/21 12:00開始まで", reference_year=2026)
        == "2026-08-21T12:00:00+09:00"
    )


def test_returns_none_for_slash_date_with_no_time():
    assert extract_event_datetime("帰ってきた！あたしンちフェア〜8/21まで", reference_year=2026) is None


def test_does_not_extract_slash_date_from_year_qualified_date():
    # "2026/08/21" must not be misread as month=08/day=21 — full year-qualified dates stay
    # out of scope entirely (see event_extraction.py's docstring on _DATE_SLASH_RE).
    assert extract_event_datetime("開催日: 2026/08/21 18時30分", reference_year=2026) is None


def test_extracts_location_from_label():
    assert extract_location("トークイベント開催、会場:渋谷ロフト9") == "渋谷ロフト9"


def test_extracts_location_from_fullwidth_colon_label():
    assert extract_location("トークイベント開催、会場：新宿伊勢丹") == "新宿伊勢丹"


def test_extracts_location_from_suffix_pattern():
    assert extract_location("渋谷ロフト9にて開催のトークイベント") == "渋谷ロフト9"


def test_does_not_extract_location_from_bare_at_mention():
    # Deliberate: on X, "@" almost always introduces an account mention, not a place — see
    # event_extraction.py's docstring.
    assert extract_location("詳細は @atashinchi_new をチェック！") is None


def test_returns_none_when_no_location_marker_present():
    assert extract_location("トークイベントを開催します。詳細は近日公開。") is None
