from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from zoneinfo import ZoneInfo

from .classifier import classify_message
from .discovery import CHANNEL_NAME, read_json, validate_exports
from .models import Attachment, ExportSelection, Message, SourceRef


SEOUL = ZoneInfo("Asia/Seoul")


def parse_exports(exports: Iterable[ExportSelection]) -> List[Message]:
    selected = list(exports)
    validate_exports(selected)
    messages: MutableMapping[str, Message] = {}

    for export in selected:
        users = _load_users(export.root / "users.json")
        for json_path in sorted((export.root / CHANNEL_NAME).glob("*.json")):
            for raw in read_json(json_path):
                message = _parse_message(raw, users, export, json_path)
                if message is None:
                    continue
                existing = messages.get(message.id)
                messages[message.id] = _merge_duplicate(existing, message) if existing else message

    return sorted(messages.values(), key=lambda message: (message.occurred_at, message.id))


def _load_users(path: Path) -> Dict[str, str]:
    users = {}
    for raw in read_json(path):
        user_id = str(raw.get("id", ""))
        profile = raw.get("profile") or {}
        users[user_id] = _first_text(
            profile.get("display_name"),
            raw.get("real_name"),
            profile.get("real_name"),
            profile.get("first_name"),
            raw.get("name"),
            user_id,
        )
    return users


def _parse_message(
    raw: Mapping[str, object],
    users: Mapping[str, str],
    export: ExportSelection,
    json_path: Path,
) -> Optional[Message]:
    if raw.get("type") != "message" or raw.get("subtype") in {"message_deleted", "tombstone"}:
        return None

    timestamp = str(raw.get("ts", ""))
    if not timestamp:
        return None

    user_id = str(raw.get("user", ""))
    profile = raw.get("user_profile") if isinstance(raw.get("user_profile"), dict) else {}
    author = _first_text(
        users.get(user_id),
        profile.get("display_name"),
        profile.get("real_name"),
        profile.get("first_name"),
        raw.get("username"),
        user_id,
        "알 수 없음",
    )
    attachments = tuple(_parse_attachments(raw.get("files")))
    text = str(raw.get("text") or "")
    category, reason = classify_message(text, attachments)
    thread_timestamp = str(raw.get("thread_ts")) if raw.get("thread_ts") else None
    is_thread_reply = bool(thread_timestamp and thread_timestamp != timestamp)

    return Message(
        id=f"{CHANNEL_NAME}:{timestamp}",
        timestamp=timestamp,
        occurred_at=datetime.fromtimestamp(float(timestamp), tz=SEOUL),
        user_id=user_id,
        author=author,
        text=text,
        thread_timestamp=thread_timestamp,
        is_thread_reply=is_thread_reply,
        category=category,
        category_reason=reason,
        attachments=attachments,
        sources=(SourceRef(export.name, str(json_path.relative_to(export.root))),),
    )


def _parse_attachments(raw_files: object) -> Iterable[Attachment]:
    if not isinstance(raw_files, list):
        return []

    attachments = []
    for index, raw in enumerate(raw_files, start=1):
        if not isinstance(raw, dict):
            continue
        mimetype = str(raw.get("mimetype") or "")
        if not mimetype.startswith("image/"):
            continue
        file_id = str(raw.get("id") or f"unknown-{index}")
        url = str(raw.get("url_private_download") or raw.get("url_private") or "")
        attachments.append(
            Attachment(
                id=file_id,
                name=str(raw.get("name") or f"image-{index}"),
                mimetype=mimetype,
                download_url=url,
                width=_optional_int(raw.get("original_w")),
                height=_optional_int(raw.get("original_h")),
            )
        )
    return attachments


def _merge_duplicate(existing: Message, incoming: Message) -> Message:
    attachments = _unique_attachments((*existing.attachments, *incoming.attachments))
    sources = tuple(sorted(set((*existing.sources, *incoming.sources)), key=lambda source: (source.export_name, source.json_path)))
    preferred = incoming if _message_score(incoming) > _message_score(existing) else existing
    return Message(
        id=preferred.id,
        timestamp=preferred.timestamp,
        occurred_at=preferred.occurred_at,
        user_id=preferred.user_id,
        author=preferred.author,
        text=preferred.text,
        thread_timestamp=preferred.thread_timestamp,
        is_thread_reply=preferred.is_thread_reply,
        category=preferred.category,
        category_reason=preferred.category_reason,
        attachments=attachments,
        sources=sources,
    )


def _unique_attachments(attachments: Tuple[Attachment, ...]) -> Tuple[Attachment, ...]:
    unique = {}
    for attachment in attachments:
        unique.setdefault(attachment.id, attachment)
    return tuple(unique.values())


def _message_score(message: Message) -> tuple[int, int, int]:
    return (len(message.text), len(message.attachments), len(message.author))


def _first_text(*values: object) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _optional_int(value: object) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
