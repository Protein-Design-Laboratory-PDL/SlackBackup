from pathlib import Path

from slack_backup.parser import parse_exports
from tests.helpers import write_export


def test_parse_and_classify_messages(tmp_path: Path):
    export = write_export(
        tmp_path / "export-a",
        [
            {
                "type": "message",
                "ts": "1767312000.000001",
                "user": "U1",
                "text": "발주 부탁드립니다",
                "files": [
                    {
                        "id": "F1",
                        "name": "order.png",
                        "mimetype": "image/png",
                        "url_private": "https://example.invalid/order.png?token=secret",
                    }
                ],
            },
            {
                "type": "message",
                "ts": "1767312060.000001",
                "thread_ts": "1767312000.000001",
                "user": "U1",
                "text": "1번 정리완료",
            },
        ],
    )

    messages = parse_exports([export])

    assert [message.category for message in messages] == ["발주 요청", "수령 확인"]
    assert messages[0].author == "테스트 연구원"
    assert messages[1].is_thread_reply is True
    assert messages[0].attachments[0].download_url.endswith("token=secret")


def test_overlapping_exports_are_deduplicated(tmp_path: Path):
    raw_message = {
        "type": "message",
        "ts": "1767312000.000001",
        "user": "U1",
        "text": "견적 요청입니다",
    }
    first = write_export(tmp_path / "export-a", [raw_message])
    second = write_export(tmp_path / "export-b", [raw_message])

    messages = parse_exports([first, second])

    assert len(messages) == 1
    assert messages[0].category == "견적 요청"
    assert len(messages[0].sources) == 2
