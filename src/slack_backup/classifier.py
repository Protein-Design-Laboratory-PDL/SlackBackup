from __future__ import annotations

import re
from typing import Tuple

from .models import Attachment


ORDER_CANCEL_PATTERN = re.compile(r"발주.{0,8}(취소|철회)|(취소|철회).{0,8}발주")
QUOTE_PATTERN = re.compile(r"견적")
ORDER_PATTERN = re.compile(r"발주|주문")
CONFIRM_PATTERN = re.compile(r"정리\s*완료|정완|수령\s*완료|수령했|찾아갔|가져갔")
RECEIPT_PATTERN = re.compile(r"도착|입고|보관|전달|명세서|택배|물품.{0,5}왔|왔습니다")


def classify_message(text: str, attachments: Tuple[Attachment, ...]) -> tuple[str, str]:
    normalized = " ".join(text.split())

    if ORDER_CANCEL_PATTERN.search(normalized):
        return "기타", "발주 취소 메시지"
    if QUOTE_PATTERN.search(normalized):
        return "견적 요청", "본문에 견적 표현이 있음"
    if CONFIRM_PATTERN.search(normalized):
        return "수령 확인", "본문에 수령 또는 정리 완료 표현이 있음"
    if RECEIPT_PATTERN.search(normalized):
        return "물품 수령", "본문에 도착·전달·보관 표현이 있음"
    if ORDER_PATTERN.search(normalized):
        return "발주 요청", "본문에 발주 또는 주문 표현이 있음"
    if not normalized and attachments:
        return "분류 불확실", "설명 없이 첨부파일만 있음"
    return "기타", "명확한 분류 표현이 없음"

