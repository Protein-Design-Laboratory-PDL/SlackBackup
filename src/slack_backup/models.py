from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class SourceRef:
    export_name: str
    json_path: str


@dataclass(frozen=True)
class Attachment:
    id: str
    name: str
    mimetype: str
    download_url: str = field(repr=False, compare=False)
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass(frozen=True)
class Message:
    id: str
    timestamp: str
    occurred_at: datetime
    user_id: str
    author: str
    text: str
    thread_timestamp: Optional[str]
    is_thread_reply: bool
    category: str
    category_reason: str
    attachments: Tuple[Attachment, ...]
    sources: Tuple[SourceRef, ...]

    @property
    def date_key(self) -> str:
        return self.occurred_at.date().isoformat()


@dataclass(frozen=True)
class StoredAttachment:
    attachment_id: str
    message_id: str
    original_name: str
    relative_path: Optional[str]
    mimetype: str
    error: Optional[str] = None

    @property
    def available(self) -> bool:
        return self.relative_path is not None


@dataclass(frozen=True)
class ExportSelection:
    root: Path
    name: str


@dataclass(frozen=True)
class ArchiveResult:
    output_dir: Path
    excel_path: Path
    html_path: Path
    message_count: int
    attachment_count: int
    failed_attachment_count: int

