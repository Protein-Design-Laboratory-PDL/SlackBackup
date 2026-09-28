# Slack 발주 기록 백업

Slack 내보내기 데이터에서 `reagent_apparatus_order` 채널을 골라 날짜순 Excel 문서와 오프라인 HTML 아카이브를 만드는 프로젝트입니다.

## 생성 결과

선택한 Slack 백업에서 다음 결과를 함께 생성합니다.

- 날짜순 전체 기록과 종류별 시트가 포함된 Excel 문서
- 브라우저에서 직접 열 수 있는 `index.html`
- 날짜별 JSON 기록
- 날짜와 메시지별로 정리된 첨부 이미지

## 요구 환경

- Python 3.9 이상
- 인터넷 연결: Slack 첨부 이미지를 처음 내려받을 때 필요
- Microsoft Excel 데스크톱: 생성된 `.xlsx` 열람

## 설치

macOS 또는 Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install .
```

## 사용 방법

1. Slack에서 내보낸 압축 파일을 해제합니다.
2. 해제한 폴더를 이 프로젝트의 `data` 폴더 아래에 그대로 넣습니다.
3. 프로젝트 루트에서 프로그램을 실행합니다.

macOS 또는 Linux:

```bash
.venv/bin/slack-backup
```

Windows PowerShell:

```powershell
.venv\Scripts\slack-backup.exe
```

화면에 나타난 백업 목록에서 번호를 선택합니다. 여러 개를 합치려면 `1,3`처럼 입력합니다. 선택한 백업의 기간이 겹쳐도 같은 메시지와 이미지는 한 번만 기록됩니다.

완성된 결과는 `outputs/SlackBackup_시작일_종료일/`에 저장됩니다. `index.html`은 별도 서버 없이 브라우저에서 직접 열 수 있습니다.

## 데이터 보호

`data`, `storage`, `outputs`는 Git에서 제외됩니다.