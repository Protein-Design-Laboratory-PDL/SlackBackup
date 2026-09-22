from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path
import shutil
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from PIL import Image as PillowImage
from PIL import ImageOps

from .models import Message, StoredAttachment


HEADER_FILL = PatternFill("solid", fgColor="284A7E")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(size=14, bold=True, color="172033")
SUBTLE_FILL = PatternFill("solid", fgColor="EEF3FA")
DATE_FILL = PatternFill("solid", fgColor="E7EEFA")
THIN_BORDER = Border(bottom=Side(style="thin", color="D8DEEA"))
CATEGORY_COLORS = {
    "발주 요청": "E8F0FE",
    "견적 요청": "FFF4D8",
    "물품 수령": "E7F6ED",
    "수령 확인": "F1EAFE",
    "분류 불확실": "FDECEC",
    "기타": "F2F4F7",
}


def write_excel(
    path: Path,
    messages: Sequence[Message],
    stored: Mapping[str, List[StoredAttachment]],
) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    preview_dir = path.parent / ".excel-previews"
    try:
        row_by_message = _write_all_messages(workbook, messages, stored, path.parent, preview_dir)
        _write_date_summary(workbook, messages, row_by_message)
        _write_category_sheet(workbook, "발주요청", messages, row_by_message, {"발주 요청", "견적 요청"})
        _write_category_sheet(workbook, "물품수령", messages, row_by_message, {"물품 수령"})
        _write_category_sheet(workbook, "수령확인", messages, row_by_message, {"수령 확인"})
        _write_attachments(workbook, messages, stored, path.parent, preview_dir, row_by_message)
        _write_order_groups(workbook, messages, row_by_message)
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.save(path)
    finally:
        shutil.rmtree(preview_dir, ignore_errors=True)


def _write_all_messages(
    workbook: Workbook,
    messages: Sequence[Message],
    stored: Mapping[str, List[StoredAttachment]],
    output_dir: Path,
    preview_dir: Path,
) -> Dict[str, int]:
    sheet = workbook.create_sheet("전체기록")
    headers = [
        "날짜", "시각", "작성자", "메시지 종류", "원문", "스레드", "첨부 수",
        "대표 이미지", "전체 이미지 위치", "메시지 ID", "원본 백업",
    ]
    _prepare_sheet(sheet, "전체 날짜순 기록", headers)
    widths = [13, 10, 20, 15, 58, 24, 10, 24, 34, 34, 28]
    _set_widths(sheet, widths)
    sheet.freeze_panes = "E5"

    row_by_message = {}
    previous_date = None
    for row_index, message in enumerate(messages, start=5):
        row_by_message[message.id] = row_index
        items = stored.get(message.id, [])
        available = [item for item in items if item.relative_path]
        thread_label = _thread_label(message)
        values = [
            message.occurred_at.date(),
            message.occurred_at.time().replace(tzinfo=None),
            message.author,
            message.category,
            message.text or "(텍스트 없음)",
            thread_label,
            len(items),
            "" if not available else available[0].original_name,
            "\n".join(item.relative_path or f"다운로드 실패: {item.original_name}" for item in items),
            message.id,
            ", ".join(source.export_name for source in message.sources),
        ]
        _append_values(sheet, row_index, values, untrusted_columns={3, 5, 8, 9, 10, 11})
        sheet.cell(row_index, 1).number_format = "yyyy-mm-dd"
        sheet.cell(row_index, 2).number_format = "hh:mm:ss"
        sheet.cell(row_index, 4).fill = PatternFill("solid", fgColor=CATEGORY_COLORS[message.category])
        for cell in sheet[row_index]:
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column in {5, 6, 9})
            cell.border = THIN_BORDER
        if previous_date != message.date_key:
            for cell in sheet[row_index]:
                cell.border = Border(top=Side(style="medium", color="8EA6CC"), bottom=THIN_BORDER.bottom)
            previous_date = message.date_key
        sheet.row_dimensions[row_index].height = 84 if available else 42
        if available:
            _add_image(
                sheet,
                output_dir / available[0].relative_path,
                preview_dir,
                f"representative-{available[0].attachment_id}",
                f"H{row_index}",
                150,
                76,
            )
            sheet.cell(row_index, 9).hyperlink = available[0].relative_path
            sheet.cell(row_index, 9).style = "Hyperlink"

    _finish_table(sheet, len(headers), len(messages))
    sheet.sheet_view.showGridLines = False
    return row_by_message


def _write_date_summary(
    workbook: Workbook,
    messages: Sequence[Message],
    row_by_message: Mapping[str, int],
) -> None:
    sheet = workbook.create_sheet("날짜별요약", 0)
    headers = ["날짜", "전체", "발주 요청", "견적 요청", "물품 수령", "수령 확인", "첨부파일", "첫 기록"]
    _prepare_sheet(sheet, "날짜별 기록 요약", headers)
    _set_widths(sheet, [14, 11, 13, 13, 13, 13, 13, 14])
    by_date = defaultdict(list)
    for message in messages:
        by_date[message.date_key].append(message)

    for row_index, (date_key, items) in enumerate(sorted(by_date.items()), start=5):
        counts = Counter(item.category for item in items)
        values = [
            date.fromisoformat(date_key),
            len(items),
            counts["발주 요청"],
            counts["견적 요청"],
            counts["물품 수령"],
            counts["수령 확인"],
            sum(len(item.attachments) for item in items),
            "전체기록 이동",
        ]
        _append_values(sheet, row_index, values)
        sheet.cell(row_index, 1).number_format = "yyyy-mm-dd"
        sheet.cell(row_index, 8).hyperlink = f"#'전체기록'!A{row_by_message[items[0].id]}"
        sheet.cell(row_index, 8).style = "Hyperlink"
        if row_index % 2:
            for cell in sheet[row_index]:
                cell.fill = SUBTLE_FILL
    _finish_table(sheet, len(headers), len(by_date))
    sheet.freeze_panes = "A5"
    sheet.sheet_view.showGridLines = False


def _write_category_sheet(
    workbook: Workbook,
    title: str,
    messages: Sequence[Message],
    row_by_message: Mapping[str, int],
    categories: set,
) -> None:
    filtered = [message for message in messages if message.category in categories]
    sheet = workbook.create_sheet(title)
    headers = ["날짜", "시각", "작성자", "종류", "원문", "첨부 수", "전체기록"]
    _prepare_sheet(sheet, title, headers)
    _set_widths(sheet, [13, 10, 20, 15, 64, 10, 14])
    for row_index, message in enumerate(filtered, start=5):
        values = [
            message.occurred_at.date(),
            message.occurred_at.time().replace(tzinfo=None),
            message.author,
            message.category,
            message.text or "(텍스트 없음)",
            len(message.attachments),
            "원문 이동",
        ]
        _append_values(sheet, row_index, values, untrusted_columns={3, 5})
        sheet.cell(row_index, 1).number_format = "yyyy-mm-dd"
        sheet.cell(row_index, 2).number_format = "hh:mm:ss"
        sheet.cell(row_index, 7).hyperlink = f"#'전체기록'!A{row_by_message[message.id]}"
        sheet.cell(row_index, 7).style = "Hyperlink"
        sheet.cell(row_index, 5).alignment = Alignment(vertical="top", wrap_text=True)
        sheet.row_dimensions[row_index].height = 36
    _finish_table(sheet, len(headers), len(filtered))
    sheet.freeze_panes = "E5"
    sheet.sheet_view.showGridLines = False


def _write_attachments(
    workbook: Workbook,
    messages: Sequence[Message],
    stored: Mapping[str, List[StoredAttachment]],
    output_dir: Path,
    preview_dir: Path,
    row_by_message: Mapping[str, int],
) -> None:
    sheet = workbook.create_sheet("첨부이미지")
    headers = ["날짜", "시각", "작성자", "파일명", "상태", "전체기록", "이미지"]
    _prepare_sheet(sheet, "첨부 이미지", headers)
    _set_widths(sheet, [13, 10, 20, 32, 18, 14, 86])
    row_index = 5
    for message in messages:
        for item in stored.get(message.id, []):
            status = "보관 완료" if item.available else item.error or "다운로드 실패"
            values = [
                message.occurred_at.date(),
                message.occurred_at.time().replace(tzinfo=None),
                message.author,
                item.original_name,
                status,
                "원문 이동",
                "",
            ]
            _append_values(sheet, row_index, values, untrusted_columns={3, 4})
            sheet.cell(row_index, 1).number_format = "yyyy-mm-dd"
            sheet.cell(row_index, 2).number_format = "hh:mm:ss"
            sheet.cell(row_index, 6).hyperlink = f"#'전체기록'!A{row_by_message[message.id]}"
            sheet.cell(row_index, 6).style = "Hyperlink"
            if item.relative_path:
                image_path = output_dir / item.relative_path
                _add_image(
                    sheet,
                    image_path,
                    preview_dir,
                    f"gallery-{item.attachment_id}",
                    f"G{row_index}",
                    580,
                    280,
                )
                sheet.cell(row_index, 4).hyperlink = item.relative_path
                sheet.cell(row_index, 4).style = "Hyperlink"
                sheet.row_dimensions[row_index].height = 215
            else:
                sheet.cell(row_index, 5).fill = PatternFill("solid", fgColor="FDECEC")
                sheet.row_dimensions[row_index].height = 36
            row_index += 1
    _finish_table(sheet, len(headers), row_index - 5)
    sheet.freeze_panes = "D5"
    sheet.sheet_view.showGridLines = False


def _write_order_groups(
    workbook: Workbook,
    messages: Sequence[Message],
    row_by_message: Mapping[str, int],
) -> None:
    sheet = workbook.create_sheet("발주건")
    headers = ["발주건 ID", "발주자", "요청 일시", "요청 원문", "연결 기록", "연결 근거"]
    _prepare_sheet(sheet, "확실하게 연결된 발주건", headers)
    _set_widths(sheet, [28, 20, 20, 58, 46, 18])
    groups = _certain_thread_groups(messages)
    for row_index, (request, linked) in enumerate(groups, start=5):
        linked_summary = "\n".join(
            f"{item.occurred_at:%Y-%m-%d %H:%M} {item.author}: {item.text or '(텍스트 없음)'}"
            for item in linked
        )
        values = [
            request.id,
            request.author,
            request.occurred_at.replace(tzinfo=None),
            request.text,
            linked_summary,
            "같은 스레드",
        ]
        _append_values(sheet, row_index, values, untrusted_columns={1, 2, 4, 5})
        sheet.cell(row_index, 3).number_format = "yyyy-mm-dd hh:mm"
        sheet.cell(row_index, 1).hyperlink = f"#'전체기록'!A{row_by_message[request.id]}"
        sheet.cell(row_index, 1).style = "Hyperlink"
        sheet.cell(row_index, 4).alignment = Alignment(vertical="top", wrap_text=True)
        sheet.cell(row_index, 5).alignment = Alignment(vertical="top", wrap_text=True)
        sheet.row_dimensions[row_index].height = min(120, 30 + len(linked) * 24)
    if not groups:
        sheet.cell(5, 1, "선택한 기록에서 확실하게 연결할 수 있는 발주건이 없습니다.")
        sheet.merge_cells(start_row=5, start_column=1, end_row=5, end_column=len(headers))
        sheet.cell(5, 1).alignment = Alignment(vertical="center")
        sheet.cell(5, 1).fill = SUBTLE_FILL
    else:
        _finish_table(sheet, len(headers), len(groups))
    sheet.freeze_panes = "A5"
    sheet.sheet_view.showGridLines = False


def _certain_thread_groups(messages: Sequence[Message]) -> List[Tuple[Message, List[Message]]]:
    requests = {
        message.timestamp: message
        for message in messages
        if message.category in {"발주 요청", "견적 요청"}
    }
    linked = defaultdict(list)
    for message in messages:
        if message.is_thread_reply and message.thread_timestamp in requests:
            linked[message.thread_timestamp].append(message)
    return [(request, linked[timestamp]) for timestamp, request in requests.items() if linked[timestamp]]


def _prepare_sheet(sheet: Worksheet, title: str, headers: Sequence[str]) -> None:
    sheet.cell(2, 1, title)
    sheet.cell(2, 1).font = TITLE_FONT
    sheet.cell(3, 1, "Asia/Seoul 기준 · 원문은 Slack 내보내기 데이터에서 가져옴")
    sheet.cell(3, 1).font = Font(size=9, italic=True, color="667085")
    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(4, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[4].height = 24


def _append_values(
    sheet: Worksheet,
    row: int,
    values: Sequence[object],
    untrusted_columns: set = frozenset(),
) -> None:
    for column, value in enumerate(values, start=1):
        cell = sheet.cell(row, column, value)
        if column in untrusted_columns and isinstance(value, str):
            cell.data_type = "s"
        cell.alignment = Alignment(vertical="center")


def _finish_table(sheet: Worksheet, column_count: int, data_count: int) -> None:
    last_row = max(4, data_count + 4)
    sheet.auto_filter.ref = f"A4:{get_column_letter(column_count)}{last_row}"


def _set_widths(sheet: Worksheet, widths: Iterable[float]) -> None:
    for column, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width


def _thread_label(message: Message) -> str:
    if not message.is_thread_reply:
        return "원문 메시지"
    return f"답글 · 원문 {message.thread_timestamp}"


def _add_image(
    sheet: Worksheet,
    path: Path,
    preview_dir: Path,
    preview_key: str,
    anchor: str,
    max_width: int,
    max_height: int,
) -> bool:
    if not path.is_file():
        return False
    try:
        preview = _create_preview(path, preview_dir, preview_key, max_width * 2, max_height * 2)
        image = ExcelImage(preview)
        ratio = min(max_width / image.width, max_height / image.height, 1)
        image.width = max(1, int(image.width * ratio))
        image.height = max(1, int(image.height * ratio))
        sheet.add_image(image, anchor)
        return True
    except (OSError, ValueError):
        return False


def _create_preview(
    source: Path,
    preview_dir: Path,
    key: str,
    max_width: int,
    max_height: int,
) -> Path:
    digest = sha256(key.encode("utf-8")).hexdigest()[:20]
    preview_dir.mkdir(parents=True, exist_ok=True)
    with PillowImage.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        image.thumbnail((max_width, max_height), PillowImage.Resampling.LANCZOS)
        has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
        if has_alpha:
            destination = preview_dir / f"{digest}.png"
            image.save(destination, format="PNG", optimize=True)
        else:
            destination = preview_dir / f"{digest}.jpg"
            image.convert("RGB").save(destination, format="JPEG", quality=84, optimize=True)
    return destination
