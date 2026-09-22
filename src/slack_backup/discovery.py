from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import ExportSelection


CHANNEL_NAME = "reagent_apparatus_order"


class InvalidExportError(ValueError):
    pass


def discover_exports(data_dir: Path) -> List[ExportSelection]:
    if not data_dir.exists():
        return []

    exports = []
    for child in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        if (child / "users.json").is_file() and (child / CHANNEL_NAME).is_dir():
            exports.append(ExportSelection(root=child, name=child.name))
    return exports


def validate_exports(exports: Iterable[ExportSelection]) -> None:
    selected = list(exports)
    if not selected:
        raise InvalidExportError("처리할 Slack 백업 폴더가 선택되지 않았습니다.")

    for export in selected:
        channel_dir = export.root / CHANNEL_NAME
        if not (export.root / "users.json").is_file():
            raise InvalidExportError(f"{export.name}: users.json 파일이 없습니다.")
        if not channel_dir.is_dir():
            raise InvalidExportError(f"{export.name}: {CHANNEL_NAME} 채널 폴더가 없습니다.")
        if not list(channel_dir.glob("*.json")):
            raise InvalidExportError(f"{export.name}: 채널 메시지 JSON 파일이 없습니다.")


def read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidExportError(f"JSON 파일을 읽을 수 없습니다: {path.name}") from exc

