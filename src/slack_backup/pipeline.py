from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Callable, Iterable, Optional

from .archive import write_archive_files
from .attachments import AttachmentStore
from .excel_writer import write_excel
from .models import ArchiveResult, ExportSelection
from .parser import parse_exports


ProgressCallback = Callable[[str], None]


def build_archive(
    exports: Iterable[ExportSelection],
    output_root: Path,
    storage_root: Path,
    progress: Optional[ProgressCallback] = None,
    attachment_store: Optional[AttachmentStore] = None,
) -> ArchiveResult:
    selected = list(exports)
    _report(progress, "Slack 메시지를 읽는 중입니다.")
    messages = parse_exports(selected)
    if not messages:
        raise ValueError("선택한 백업에 처리할 메시지가 없습니다.")

    archive_name = f"SlackBackup_{messages[0].date_key}_{messages[-1].date_key}"
    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{archive_name}-", dir=output_root))

    try:
        _report(progress, "첨부 이미지를 보관하는 중입니다.")
        store = attachment_store or AttachmentStore(storage_root / "attachments")
        stored = store.materialize(messages, staging)

        _report(progress, "날짜별 HTML 아카이브를 만드는 중입니다.")
        write_archive_files(staging, messages, stored, selected)

        _report(progress, "Excel 문서를 만드는 중입니다.")
        excel_name = f"Slack_발주기록_{messages[0].date_key}_{messages[-1].date_key}.xlsx"
        write_excel(staging / excel_name, messages, stored)

        final_dir = output_root / archive_name
        _replace_completed_archive(staging, final_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    attachments = [item for items in stored.values() for item in items]
    _report(progress, f"완료: {final_dir}")
    return ArchiveResult(
        output_dir=final_dir,
        excel_path=final_dir / excel_name,
        html_path=final_dir / "index.html",
        message_count=len(messages),
        attachment_count=len(attachments),
        failed_attachment_count=sum(not item.available for item in attachments),
    )


def _replace_completed_archive(staging: Path, final_dir: Path) -> None:
    previous = final_dir.with_name(f".{final_dir.name}.previous")
    if previous.exists():
        shutil.rmtree(previous)
    if final_dir.exists():
        final_dir.replace(previous)
    try:
        staging.replace(final_dir)
    except Exception:
        if previous.exists() and not final_dir.exists():
            previous.replace(final_dir)
        raise
    shutil.rmtree(previous, ignore_errors=True)


def _report(callback: Optional[ProgressCallback], message: str) -> None:
    if callback:
        callback(message)

