from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from .discovery import InvalidExportError, discover_exports
from .models import ExportSelection
from .pipeline import build_archive


def main() -> int:
    project_root = Path.cwd()
    exports = discover_exports(project_root / "data")
    if not exports:
        print("data 폴더에서 Slack 내보내기 데이터를 찾지 못했습니다.")
        return 1

    print("\n처리할 Slack 백업을 선택하세요. 여러 개는 쉼표로 구분합니다.\n")
    for index, export in enumerate(exports, start=1):
        print(f"  {index}. {export.name}")
    print("  a. 전체 선택")

    try:
        selected = _read_selection(exports)
        result = build_archive(
            selected,
            output_root=project_root / "outputs",
            storage_root=project_root / "storage",
            progress=lambda message: print(f"\n{message}"),
        )
    except (InvalidExportError, ValueError) as exc:
        print(f"\n입력 오류: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n작업을 취소했습니다.")
        return 130
    except Exception:
        print("\n아카이브 생성 중 오류가 발생했습니다. 원본 데이터는 변경되지 않았습니다.")
        return 1

    print(f"  메시지: {result.message_count}개")
    print(f"  첨부파일: {result.attachment_count}개")
    if result.failed_attachment_count:
        print(f"  다운로드 실패: {result.failed_attachment_count}개")
    print(f"  Excel: {result.excel_path}")
    print(f"  HTML: {result.html_path}")
    return 0


def _read_selection(exports: List[ExportSelection]) -> List[ExportSelection]:
    while True:
        raw = input("\n선택: ").strip().lower()
        if raw == "a":
            return exports
        try:
            indices = {int(value.strip()) for value in raw.split(",") if value.strip()}
        except ValueError:
            indices = set()
        if indices and all(1 <= index <= len(exports) for index in indices):
            return [exports[index - 1] for index in sorted(indices)]
        print("목록의 번호를 입력하세요. 예: 1 또는 1,3")


if __name__ == "__main__":
    sys.exit(main())

