import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from slack_backup.archive import write_archive_files
from slack_backup.models import ExportSelection, Message, SourceRef, StoredAttachment


def test_archive_contains_safe_records_and_offline_html(tmp_path: Path):
    message = Message(
        id="reagent_apparatus_order:1.1",
        timestamp="1.1",
        occurred_at=datetime(2026, 1, 2, 9, 30, tzinfo=ZoneInfo("Asia/Seoul")),
        user_id="U1",
        author="연구원",
        text="발주 부탁드립니다 </script>",
        thread_timestamp=None,
        is_thread_reply=False,
        category="발주 요청",
        category_reason="본문에 발주 표현이 있음",
        attachments=(),
        sources=(SourceRef("sample", "reagent_apparatus_order/2026-01-02.json"),),
    )
    stored = {
        message.id: [
            StoredAttachment(
                attachment_id="F1",
                message_id=message.id,
                original_name="image.png",
                relative_path="attachments/2026-01-02/1_1/01_image.png",
                mimetype="image/png",
            )
        ]
    }

    write_archive_files(
        tmp_path,
        [message],
        stored,
        [ExportSelection(tmp_path / "sample", "sample")],
    )

    records = json.loads((tmp_path / "records" / "2026-01-02.json").read_text(encoding="utf-8"))
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert records[0]["text"].endswith("</script>")
    assert records[0]["attachments"][0]["path"].startswith("attachments/")
    assert "token=" not in html
    assert "\\u003c/script>" in html

