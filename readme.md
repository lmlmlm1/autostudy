# AutoStudy

> 의과대학 강의의 **PDF 강의록**과 **음성 녹음**을 결합하여, 교정된 슬라이드별 스크립트·단권화 노트·Anki 덱·Notion 페이지·복습용 PDF를 만드는 개인용 학습 파이프라인입니다.


## 처리 흐름

| 단계 | 실행 위치 | 입력 | 핵심 동작 | 산출물 |
|---|---|---|---|---|
| 1. 강의록 준비 | 로컬 `WATCH_PATH/lecture/` | 줄필기·야붙 PDF 또는 이미 병합된 PDF | 파일명 정리와 PDF 병합 | `WATCH_PATH/{base_name}.pdf` |
| 2. 1차 처리 | 로컬 | 원본 PDF | 페이지별 텍스트 추출, OCR 보완, Whisper 초기 프롬프트 생성 | `_강의자료.txt`, `_whisperkeyword.txt` |
| 3. 음성 전사 | Google Colab | `.m4a` 또는 변환 가능한 `.mp4`, 키워드 파일 | Whisper `medium` 모델로 한국어 전사 | `_음성스크립트.txt` |
| 4. 2차 처리 | 로컬 | 원본 PDF·음성 파일과 두 텍스트 파일 | 스크립트 교정, 요약, 결과 폴더 이동 | 교정본, JSON, 강의별 폴더 |
| 5. 연동·출력 | 로컬 및 연동 서비스 | 처리 완료 강의 폴더 | Notion 업로드, Anki 생성, 복습용 PDF 생성 | Notion 페이지, CSV·APKG, `_scripted.pdf` |
| 6. 날짜별 합본 | 로컬 수동 실행 | 여러 강의의 `_scripted.pdf` | 같은 날짜 강의의 복습용 PDF 병합 | `merged/{날짜}_merged_scripted.pdf` |

`main.py`는 매번 같은 초기 스캔을 수행합니다. 따라서 “1차 실행”과 “2차 실행”은 별도 스크립트가 아니라, **Colab 전사 파일이 생기기 전과 후에 같은 명령을 다시 실행하는 절차**입니다. 다만 2차 처리 시에는 `{base_name}.pdf` 또는 같은 base name의 음성 파일이 `WATCH_PATH` 루트에 남아 있어야 해당 base name으로 매칭 검사가 실행됩니다.

## 지원 환경과 사전 준비

현재 구현은 `WATCH_PATH + r"\lecture"` 형식의 경로 결합과 `pywin32` 의존성을 포함하므로 **Windows 환경을 기준**으로 사용하십시오. macOS·Linux는 패키지와 경로 처리의 정리가 선행되지 않으면 정상 동작을 보장하지 않습니다.

PDF가 이미지 스캔본인 경우 `extract/pdf_extract.py`는 Tesseract OCR을 `kor+eng` 언어 설정으로 호출합니다. 따라서 해당 경우에는 Python 패키지 외에 **Tesseract OCR 프로그램과 한국어·영어 언어 데이터**가 운영체제에 설치되어 있어야 합니다.

```powershell
# 1) 프로젝트 폴더로 이동
cd autostudy-main

# 2) 가상환경 생성 및 활성화
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Python 의존성 설치
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4) 환경 변수 파일 생성
copy env.example .env
```

> PowerShell 실행 정책 때문에 활성화가 막히면 현재 세션에서 `Set-ExecutionPolicy -Scope Process Bypass`를 실행한 뒤 다시 활성화하십시오.

## 환경 변수

`.env`에는 아래 값을 설정합니다. `API_KEY`와 `WATCH_PATH`는 파이프라인의 기본 실행에 필요하며, Notion·Google Drive 결과 연동을 쓸 경우 Notion 항목도 설정해야 합니다.

| 변수 | 필요 여부 | 현재 코드에서의 용도 |
|---|---:|---|
| `API_KEY` | 필수 | Gemini 키워드 추출, 스크립트 교정, 요약, Anki 카드 생성 |
| `WATCH_PATH` | 필수 | Google Drive 동기화 작업 폴더의 절대 경로 |
| `NOTION_TOKEN` | Notion 사용 시 필수 | Notion API 클라이언트 인증 |
| `NOTION_DATABASE_ID` | Notion 사용 시 필수 | 새 강의 페이지를 생성할 데이터베이스 |
| `NOTION_DATA_SOURCE_ID` | Anki 링크 추가 시 필수 | 업로드한 Notion 페이지를 다시 찾는 데이터 소스 |
| `SPARE_KEY` | 현재 미사용 | `env.example`에는 있으나 현재 소스에서 참조하지 않음 |
| `NOTION_PAGE_ID` | 현재 미사용 | `env.example`에는 있으나 현재 소스에서 참조하지 않음 |

예시는 다음과 같습니다.

```dotenv
API_KEY=your_gemini_api_key
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATA_SOURCE_ID=collection_or_data_source_id
WATCH_PATH=G:\내 드라이브\2026-1
```

### Google Drive OAuth 준비

Notion 페이지에는 Google Drive에 동기화된 원본 PDF와 Anki 파일의 링크가 사용됩니다. 프로젝트 루트에 Google Cloud OAuth 클라이언트 파일인 `credentials.json`을 두십시오. 최초 실행 시 브라우저 인증이 진행되며, 이후에는 `token.pickle`이 생성되어 재사용됩니다. 두 파일과 `.env`는 `.gitignore`에 포함되어 있으므로 저장소에 커밋하지 마십시오.

Google Drive 검색은 **파일명 완전 일치**로 첫 번째 검색 결과를 사용합니다. 동기화 대상 Drive 안에 같은 이름의 PDF·이미지·Anki 파일이 중복되지 않도록 관리하는 편이 안전합니다.

## 작업 폴더와 파일명 규칙

`WATCH_PATH`는 Google Drive Desktop 등이 동기화하는 로컬 작업 폴더를 뜻합니다. 최소 구조는 아래와 같습니다.

```text
WATCH_PATH/
├── lecture/                    # 병합 전 줄필기·야붙 PDF를 넣는 폴더
├── merged/                     # 날짜별 합본의 저장 폴더 — 직접 만들어야 함
├── 0123_1.m4a                  # 강의 녹음
├── 0123_1.pdf                  # 병합 완료 원본 강의록
├── 0123_1_강의자료.txt          # 1차 실행 산출물
├── 0123_1_whisperkeyword.txt   # 1차 실행 산출물
└── 0123_1_음성스크립트.txt       # Colab 전사 산출물
```

`base_name`은 강의 단위를 식별하는 공통 파일명입니다. 현재 구현과 가장 잘 맞는 형식은 `MMDD_교시번호`이며, 예를 들어 `0123_1`을 사용합니다. 원본 PDF와 음성 파일, 그리고 생성되는 모든 텍스트 파일은 반드시 같은 base name을 공유해야 합니다.

### 강의록 병합 규칙

초기 스캔은 `lecture/`의 PDF를 먼저 정리합니다. 구현은 파일명 **앞 여섯 글자**를 식별자처럼 사용하며, 줄필기와 야붙 파일을 짝지어 병합합니다. 파일명 끝이 `야붙필기.pdf` 또는 `야붙.pdf.pdf`인 자료는 이미 병합된 것으로 보고, 병합하지 않고 `WATCH_PATH/{앞 여섯 글자}.pdf`로 복사합니다. 야붙·줄필기 쌍이 모두 있는 경우에만 최종 PDF를 만듭니다.

따라서 파일명 규칙이 다르거나 앞 여섯 글자가 같은 서로 다른 강의가 있으면 잘못 묶일 수 있습니다. 자료를 넣기 전에 `MMDD_교시번호`가 앞 여섯 글자에서 고유하도록 정리하십시오.

## 실행 방법

### 1. 강의록 텍스트와 Whisper 키워드 만들기

`WATCH_PATH/lecture/`에 강의록 PDF를 넣고, 녹음 파일은 `WATCH_PATH` 루트에 둡니다. 병합이 필요 없는 원본 PDF도 최종적으로 `WATCH_PATH/{base_name}.pdf`가 되도록 준비하십시오.

```powershell
python main.py
```

이 실행은 다음 순서로 동작합니다.

1. `lecture/` 안의 줄필기·야붙 PDF를 정리하고 가능한 쌍을 병합합니다.
2. `WATCH_PATH` 루트의 각 PDF에서 텍스트를 추출합니다. 텍스트 레이어가 거의 없으면 OCR을 시도하며, 페이지 구분자는 `--- N Page ---` 형식으로 남깁니다.
3. Gemini가 Whisper의 초기 프롬프트로 쓸 의학용어를 생성하고 `{base_name}_whisperkeyword.txt`에 저장합니다.
4. 아직 `{base_name}_음성스크립트.txt`가 없으면 교정·요약 단계는 실행하지 않습니다.

### 2. Google Colab에서 음성 전사하기

[`colab/Transcribe.ipynb`](./colab/Transcribe.ipynb)를 Google Colab에서 열어 실행합니다. 전사 셀의 `folder_path`는 현재 다음 경로로 하드코딩되어 있습니다.

```python
folder_path = "/content/drive/MyDrive/2026-1"
```

실제 Drive 폴더와 다르면 이 값을 수정한 뒤, Drive 마운트 → 필요 시 MP4를 M4A로 변환 → Whisper 설치 → 전사 셀 순으로 실행하십시오. 노트북은 `.m4a` 파일만 전사하며, Whisper `medium` 모델과 `language="ko"`를 사용합니다.

각 M4A에 대해 해당 이름의 `_whisperkeyword.txt`가 있어야 전사를 시작합니다. 키워드 파일이 없으면 현재 노트북은 기본 프롬프트로 대체하지 않고 그 파일을 건너뜁니다. 이미 `_음성스크립트.txt`가 있으면 중복 전사를 막기 위해 건너뜁니다.

성공하면 Drive 작업 폴더에 다음 파일이 생성됩니다.

```text
{base_name}_음성스크립트.txt
```

### 3. 교정·요약·연동 결과 만들기

전사가 끝난 뒤 원본 PDF와 음성 파일, `_강의자료.txt`, `_음성스크립트.txt`가 모두 `WATCH_PATH` 루트에 있는지 확인하고 다시 실행합니다.

```powershell
python main.py
```

동일 base name의 `_강의자료.txt`와 `_음성스크립트.txt`가 모두 있으면 Gemini가 강의록을 참고하여 스크립트를 교정하고, `[Slide 001]` 형식의 슬라이드별 본문과 시험 대비용 단권화 요약을 생성합니다. 성공한 관련 파일은 `WATCH_PATH/{base_name}/`으로 이동합니다.

처리 순서는 **Notion 업로드 → Anki 생성 → 복습용 PDF 생성**입니다. Notion 업로드가 성공해야 `_result.json`이 `_done.json`으로 이름이 바뀌며, 복습용 PDF 생성은 이 `_done.json`을 요구합니다. 따라서 Notion 업로드가 실패하면 Anki 생성은 시도될 수 있으나 `_scripted.pdf`는 생성되지 않습니다.

## 강의별 결과물

처리 후 주요 파일은 `WATCH_PATH/{base_name}/`에 위치합니다.

| 파일 | 설명 | 생성 시점 |
|---|---|---|
| `{base_name}.pdf` | 병합·정리된 원본 강의록 | 1차 처리 전 또는 중 |
| `{base_name}.m4a` 등 | 원본 녹음 파일 | 사용자가 준비 |
| `{base_name}_강의자료.txt` | PDF 텍스트와 페이지 구분자 | 1차 처리 |
| `{base_name}_whisperkeyword.txt` | Whisper 초기 프롬프트 | 1차 처리 |
| `{base_name}_음성스크립트.txt` | Whisper 전사 결과 | Colab |
| `{base_name}_최종교정본.txt` | 슬라이드별로 매핑한 Gemini 교정본 | 2차 처리 |
| `{base_name}_result.json` | 교정본·요약·타임스탬프가 담긴 처리 중간 결과 | Notion 업로드 전 또는 업로드 실패 시 |
| `{base_name}_done.json` | Notion 업로드 성공 후 이름이 변경된 최종 처리 기록 | Notion 업로드 성공 시 |
| `{base_name}_Basic.csv` | 일반 문답형 Anki 카드 | Anki 생성 시 |
| `{base_name}_MCQ.csv` | 객관식형 Anki 카드 | Anki 생성 시 |
| `{base_name}_Cloze.csv` | 빈칸형 Anki 카드 | Anki 생성 시 |
| `{base_name}_통합본.apkg` | 세 종류 덱을 포함한 Anki 패키지 | Anki 생성 시 |
| `{base_name}_scripted.pdf` | 요약 페이지와 슬라이드·교정 스크립트를 결합한 복습용 PDF | Notion 업로드 성공 후 |

`_scripted.pdf`는 원본 PDF에 단순히 텍스트를 덧붙이는 파일이 아닙니다. 요약을 먼저 A4 페이지로 렌더링하고, 이후 각 슬라이드를 A4 상단에 배치한 뒤 슬라이드별 교정 스크립트를 하단에 렌더링한 새 PDF입니다. 스크립트가 길면 하나의 원본 슬라이드가 여러 PDF 페이지를 차지할 수 있습니다.

## Notion과 Anki 연동

Notion에는 제목, 원본 PDF Drive 링크, 상태 속성이 생성되며, 본문에는 핵심 요약과 슬라이드별 스크립트가 올라갑니다. Google Drive에 `{base_name}_001.png` 같은 슬라이드 이미지가 이미 있으면 해당 이미지 링크도 삽입합니다. 그러나 현재 `main.py`에서는 PDF 페이지 이미지를 만드는 호출이 주석 처리되어 있으므로, 이미지를 별도로 만들거나 Drive에 두지 않으면 Notion에는 텍스트 중심으로 업로드됩니다.

Anki 생성은 Basic·MCQ·Cloze CSV 세 파일과 통합 `.apkg` 패키지를 만듭니다. 생성 직후 Notion 데이터 소스에서 해당 강의 페이지를 다시 찾아, Drive에서 발견한 Anki 파일 링크를 페이지 하단에 덧붙입니다. Drive 동기화 또는 업로드가 아직 끝나지 않으면 링크 추가에 실패할 수 있습니다.

## 날짜별 복습용 PDF 합치기

개별 강의의 `_scripted.pdf`가 모두 만들어진 뒤 실행합니다. 실행 전에 `WATCH_PATH/merged/` 폴더를 직접 만들어야 합니다. 현재 유틸리티는 이 폴더를 자동 생성하지 않습니다.

```powershell
python utility/merge_pdf.py
```

날짜 문자열(예: `0123`)을 입력하면 `0123_1`, `0123_2` 등 해당 날짜로 시작하는 강의 폴더를 숫자 순으로 찾고, 각 폴더의 `{폴더명}_scripted.pdf`를 합칩니다. 대상 중 하나라도 파일이 없으면 저장하지 않고 종료하므로, 누락된 강의를 먼저 처리한 뒤 다시 실행하십시오.

## 재실행과 복구 시 유의사항

처리 완료 뒤에는 관련 파일이 강의별 하위 폴더로 이동하며, `_done.json`이 있으면 같은 강의의 AI 처리 재실행을 막습니다. 특정 강의를 처음부터 다시 처리하려면 반드시 결과를 백업한 뒤, 필요한 원본 PDF·음성 파일·텍스트 파일을 `WATCH_PATH` 루트로 되돌리고 해당 강의 폴더의 `_done.json`을 제거하는 방식으로 상태를 수동 초기화해야 합니다.

현재 파일 이동 조건은 `base_name`으로 시작하는 모든 파일을 대상으로 합니다. 예를 들어 `0123_1` 처리 중 `0123_10`도 같은 루트에 있으면 함께 이동할 수 있으므로, 접두사가 겹치는 이름을 동시에 루트에 두지 않는 것이 안전합니다.

## 프로젝트 구조

```text
.
├── main.py                         # 수동 초기 스캔 진입점
├── study_handler.py                # 파일 매칭, 교정·요약, 결과 폴더 이동
├── extract/
│   └── pdf_extract.py              # PDF 텍스트 추출 및 OCR 보완
├── process/
│   ├── llm_gemini.py               # 키워드 추출, 교정, 요약
│   ├── notion_sync.py               # Notion 업로드 및 Anki 링크 추가
│   └── anki_generator.py           # CSV·APKG Anki 덱 생성
├── upload/
│   └── google_drive.py             # Drive 파일 링크 조회와 OAuth 인증
├── utility/
│   ├── merge_jul_yaboot.py         # 줄필기·야붙 PDF 정리 및 병합
│   ├── make_scripted_pdf.py        # 복습용 PDF 생성
│   └── merge_pdf.py                # 날짜별 복습용 PDF 수동 병합
├── colab/
│   └── Transcribe.ipynb            # Google Colab Whisper 전사 노트북
├── env.example
└── requirements.txt
```

## 보안 및 개인정보 유의사항

강의 녹음, 강의자료, 전사문, 요약문은 외부 AI·Notion·Google Drive 서비스로 전달되거나 저장될 수 있습니다. 강의 제공자의 이용 조건, 녹음 동의, 소속 기관의 보안 정책 및 개인정보 보호 요건을 확인한 뒤 사용하십시오. API 키·OAuth 인증 파일·토큰은 절대 공유하거나 커밋하지 마십시오.
