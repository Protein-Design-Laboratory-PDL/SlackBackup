from pathlib import Path

from PIL import Image

from slack_backup.models import StoredAttachment
from slack_backup.pipeline import build_archive
from tests.helpers import write_export


class FakeAttachmentStore:
    def materialize(self, messages, output_dir):
        result = {}
        for message in messages:
            items = []
            for index, attachment in enumerate(message.attachments, start=1):
                relative = Path("attachments") / message.date_key / "message" / f"{index:02d}.png"
                destination = output_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (120, 80), "navy").save(destination)
                items.append(
                    StoredAttachment(
                        attachment_id=attachment.id,
                        message_id=message.id,
                        original_name=attachment.name,
                        relative_path=relative.as_posix(),
                        mimetype=attachment.mimetype,
                    )
                )
            result[message.id] = items
        return result


def test_pipeline_generates_excel_and_folder_archive(tmp_path: Path):
    export = write_export(
        tmp_path / "data" / "export-a",
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
                        "url_private": "https://example.invalid/?token=secret",
                    }
                ],
            }
        ],
    )

    result = build_archive(
        [export],
        output_root=tmp_path / "outputs",
        storage_root=tmp_path / "storage",
        attachment_store=FakeAttachmentStore(),
    )

    assert result.excel_path.is_file()
    assert result.html_path.is_file()
    assert (result.output_dir / "manifest.json").is_file()
    assert list((result.output_dir / "records").glob("*.json"))
    assert list((result.output_dir / "attachments").rglob("*.png"))
