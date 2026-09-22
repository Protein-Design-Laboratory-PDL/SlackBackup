import json
from pathlib import Path

from slack_backup.models import ExportSelection


def write_export(root: Path, messages: list[dict]) -> ExportSelection:
    channel = root / "reagent_apparatus_order"
    channel.mkdir(parents=True)
    (root / "users.json").write_text(
        json.dumps(
            [
                {
                    "id": "U1",
                    "real_name": "연구원",
                    "profile": {"display_name": "테스트 연구원"},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (channel / "2026-01-02.json").write_text(
        json.dumps(messages, ensure_ascii=False),
        encoding="utf-8",
    )
    return ExportSelection(root=root, name=root.name)

