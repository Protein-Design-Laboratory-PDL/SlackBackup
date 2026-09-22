from __future__ import annotations

import mimetypes
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from .models import Attachment, Message, StoredAttachment


INVALID_FILENAME = re.compile(r"[^0-9A-Za-z가-힣._-]+")


class AttachmentStore:
    def __init__(self, cache_dir: Path, timeout_seconds: int = 30):
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds

    def materialize(
        self,
        messages: Iterable[Message],
        output_dir: Path,
    ) -> Dict[str, List[StoredAttachment]]:
        stored: Dict[str, List[StoredAttachment]] = {}
        for message in messages:
            stored[message.id] = [
                self._materialize_one(message, attachment, index, output_dir)
                for index, attachment in enumerate(message.attachments, start=1)
            ]
        return stored

    def _materialize_one(
        self,
        message: Message,
        attachment: Attachment,
        index: int,
        output_dir: Path,
    ) -> StoredAttachment:
        extension = _extension_for(attachment)
        cache_path = self.cache_dir / f"{_safe_component(attachment.id)}{extension}"
        relative_path = Path("attachments") / message.date_key / _message_key(message) / (
            f"{index:02d}_{_safe_filename(attachment.name, extension)}"
        )
        destination = output_dir / relative_path

        try:
            if not cache_path.is_file() or cache_path.stat().st_size == 0:
                self._download(attachment, cache_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cache_path, destination)
            return StoredAttachment(
                attachment_id=attachment.id,
                message_id=message.id,
                original_name=attachment.name,
                relative_path=relative_path.as_posix(),
                mimetype=attachment.mimetype,
            )
        except urllib.error.HTTPError as exc:
            error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError):
            error = "네트워크 오류"
        except OSError:
            error = "파일 저장 오류"

        return StoredAttachment(
            attachment_id=attachment.id,
            message_id=message.id,
            original_name=attachment.name,
            relative_path=None,
            mimetype=attachment.mimetype,
            error=error,
        )

    def _download(self, attachment: Attachment, cache_path: Path) -> None:
        if not attachment.download_url:
            raise urllib.error.URLError("missing URL")

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(f"{cache_path.suffix}.part")
        request = urllib.request.Request(
            attachment.download_url,
            headers={"User-Agent": "SlackOrderBackup/0.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                with temporary.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
            if temporary.stat().st_size == 0:
                raise OSError("empty download")
            temporary.replace(cache_path)
        finally:
            temporary.unlink(missing_ok=True)


def _extension_for(attachment: Attachment) -> str:
    suffix = Path(attachment.name).suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    return mimetypes.guess_extension(attachment.mimetype) or ".img"


def _safe_filename(name: str, fallback_extension: str) -> str:
    cleaned = INVALID_FILENAME.sub("_", Path(name).name).strip("._")
    if not cleaned:
        return f"image{fallback_extension}"
    if not Path(cleaned).suffix:
        cleaned += fallback_extension
    return cleaned[:150]


def _safe_component(value: str) -> str:
    return INVALID_FILENAME.sub("_", value).strip("._") or "unknown"


def _message_key(message: Message) -> str:
    return message.timestamp.replace(".", "_")

