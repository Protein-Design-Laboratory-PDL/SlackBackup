from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from . import __version__
from .html_view import render_html
from .models import ExportSelection, Message, StoredAttachment


def write_archive_files(
    output_dir: Path,
    messages: Sequence[Message],
    stored: Mapping[str, List[StoredAttachment]],
    exports: Iterable[ExportSelection],
) -> None:
    records_dir = output_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)

    by_date: Dict[str, List[dict]] = defaultdict(list)
    all_records = []
    for message in messages:
        record = message_record(message, stored.get(message.id, []), messages)
        by_date[message.date_key].append(record)
        all_records.append(record)

    for date_key, records in sorted(by_date.items()):
        _write_json(records_dir / f"{date_key}.json", records)

    manifest = _build_manifest(messages, stored, exports)
    _write_json(output_dir / "manifest.json", manifest)
    (output_dir / "index.html").write_text(
        render_html(all_records, manifest),
        encoding="utf-8",
    )


def message_record(
    message: Message,
    stored: Sequence[StoredAttachment],
    all_messages: Sequence[Message],
) -> dict:
    known_timestamps = {item.timestamp for item in all_messages}
    parent_id = (
        f"reagent_apparatus_order:{message.thread_timestamp}"
        if message.is_thread_reply and message.thread_timestamp
        else None
    )
    return {
        "id": message.id,
        "timestamp": message.timestamp,
        "date": message.date_key,
        "time": message.occurred_at.strftime("%H:%M:%S"),
        "occurredAt": message.occurred_at.isoformat(),
        "author": message.author,
        "userId": message.user_id,
        "text": message.text,
        "category": message.category,
        "categoryReason": message.category_reason,
        "isThreadReply": message.is_thread_reply,
        "threadParentId": parent_id,
        "threadParentMissing": bool(
            message.is_thread_reply
            and message.thread_timestamp
            and message.thread_timestamp not in known_timestamps
        ),
        "attachments": [
            {
                "id": item.attachment_id,
                "name": item.original_name,
                "path": item.relative_path,
                "mimetype": item.mimetype,
                "error": item.error,
            }
            for item in stored
        ],
        "sources": [
            {"export": source.export_name, "file": source.json_path}
            for source in message.sources
        ],
    }


def _build_manifest(
    messages: Sequence[Message],
    stored: Mapping[str, List[StoredAttachment]],
    exports: Iterable[ExportSelection],
) -> dict:
    attachments = [item for items in stored.values() for item in items]
    categories = Counter(message.category for message in messages)
    source_message_count = sum(len(message.sources) for message in messages)
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "timezone": "Asia/Seoul",
        "version": __version__,
        "selectedExports": [export.name for export in exports],
        "dateRange": {
            "start": messages[0].date_key if messages else None,
            "end": messages[-1].date_key if messages else None,
        },
        "counts": {
            "messages": len(messages),
            "threadReplies": sum(message.is_thread_reply for message in messages),
            "attachments": len(attachments),
            "downloadedAttachments": sum(item.available for item in attachments),
            "failedAttachments": sum(not item.available for item in attachments),
            "duplicateMessageOccurrencesRemoved": source_message_count - len(messages),
            "categories": dict(sorted(categories.items())),
        },
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

