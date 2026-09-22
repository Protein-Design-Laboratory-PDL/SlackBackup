from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import load_workbook
from PIL import Image

from slack_backup.excel_writer import write_excel
from slack_backup.models import Message, SourceRef, StoredAttachment


def test_excel_contains_chronological_views_and_embedded_image(tmp_path: Path):
    image_path = tmp_path / "attachments" / "2026-01-02" / "1_1" / "01_image.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (2000, 1200), "navy").save(image_path)
    message = Message(
        id="reagent_apparatus_order:1.1",
        timestamp="1.1",
        occurred_at=datetime(2026, 1, 2, 9, 30, tzinfo=ZoneInfo("Asia/Seoul")),
        user_id="U1",
        author="=HYPERLINK(\"bad\")",
        text="발주 부탁드립니다",
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
    output = tmp_path / "archive.xlsx"

    write_excel(output, [message], stored)

    workbook = load_workbook(output, data_only=False)
    assert workbook.sheetnames[:2] == ["날짜별요약", "전체기록"]
    assert workbook["전체기록"]["C5"].data_type == "s"
    assert workbook["전체기록"]["C5"].value.startswith("=HYPERLINK")
    assert len(workbook["전체기록"]._images) == 1
    assert len(workbook["첨부이미지"]._images) == 1
    message_image = workbook["전체기록"]._images[0].anchor.ext
    gallery_image = workbook["첨부이미지"]._images[0].anchor.ext
    assert message_image.cx / 9525 >= 380
    assert gallery_image.cx / 9525 >= 860
    assert workbook["전체기록"].column_dimensions["H"].width == 68
    assert workbook["첨부이미지"].column_dimensions["G"].width == 250
