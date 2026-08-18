# autostudy

의대 강의 자료(강의록 PDF + 녹음 파일)를 자동으로 교정·요약하고, Anki 카드와 Notion 노트까지 생성하는 개인용 학습 자동화 파이프라인.

## 전체 흐름

```
1. lecture/ 에 강의록(_jul, _yaboot) PDF 넣기
        │
        ▼
2. main.py 1차 실행
   ├─ merge_jul_yaboot → 줄필기 + 야붙 병합 PDF 생성
   ├─ PDF 텍스트 추출 → {base_name}_강의자료.txt
   └─ Gemini로 whisper용 키워드 프롬프트 생성
        │
        ▼
3. Colab에서 Transcribe.ipynb 실행
   ├─ mp4 → m4a 변환 (녹음이 영상으로 되어 있는 경우)
   ├─ Whisper로 음성 전사
   └─ {base_name}_음성스크립트.txt 생성 (Google Drive에 저장됨)
        │
        ▼
4. main.py 2차 실행
   ├─ _강의자료.txt + _음성스크립트.txt 쌍이 맞으면 매칭 성공
   ├─ Gemini로 스크립트 교정 (correct_script_with_gemini)
   ├─ Gemini로 단권화 요약 노트 생성 (key_summary_with_gemini)
   ├─ 결과를 {base_name}_result.json으로 저장, 관련 파일을 {base_name}/ 폴더로 이동
   ├─ Notion 페이지 업로드
   ├─ Anki 카드(csv) 생성
   └─ 원본 PDF에 교정된 스크립트를 이어붙인 {base_name}_scripted.pdf 생성
        │
        ▼
5. utility/merge_pdf.py 수동 실행
   └─ 같은 날짜의 {base_name}_scripted.pdf들을 순서대로 합쳐
      merged/{날짜}_merged_scripted.pdf 생성
```

`main.py`는 실행할 때마다 같은 로직(`initial_scan`)을 도는데, **강의자료 텍스트와 음성 스크립트 텍스트가 둘 다 존재할 때만** AI 교정 단계로 넘어가도록 되어 있음 (`study_handler.py`의 `check_and_start_ai_correction`). 그래서 "1차 실행"과 "2차 실행"은 서로 다른 스크립트가 아니라, **Colab에서 음성스크립트 파일이 생기기 전/후에 같은 스크립트를 다시 돌리는 것**뿐임 — 파일이 갖춰지지 않았으면 자동으로 대기 상태로 넘어가고, 갖춰지면 그 시점에 처리됨.

## 폴더 구조

```
autostudy/
├── main.py                        # 파이프라인 진입점
├── study_handler.py                # 파일 매칭, 교정/요약 트리거, 결과 폴더 이동
├── utils.py                        # (참고용 구버전 main.py — 사용 안 함)
├── requirements.txt
├── env.example
├── extract/
│   ├── pdf_extract.py               # PDF → 텍스트
│   ├── pdf_image_save.py            # PDF → 슬라이드 이미지
│   ├── audio_extract_windows.py     # (현재 미사용, Colab이 대체)
│   └── audio_extract_mac.py         # (현재 미사용, Colab이 대체)
├── process/
│   ├── llm_gemini.py                # Gemini 교정/요약/키워드 추출
│   ├── notion_sync.py               # Notion 업로드
│   └── anki_generator.py            # Anki 카드 생성
├── upload/
│   └── google_drive.py              # Google Drive 파일 링크 조회 (Notion용)
├── utility/
│   ├── merge_jul_yaboot.py          # 줄필기 + 야붙 PDF 자동 병합
│   ├── merge_pdf.py / merge_video.py / rip_pdf.py / dowload_youtube.py
│   ├── make_scripted_pdf.py         # 원본 PDF에 교정 스크립트 삽입
│   └── fonts/                       # PDF 생성용 폰트
└── colab/
    ├── Transcribe.ipynb             # Google Colab에서 실행 (Whisper 전사 전용)
    └── readme.md
```

## 사전 준비

### 1. 가상환경 및 패키지 설치
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정
`env.example`을 복사해 `.env` 생성 후 실제 값 입력:
```bash
copy env.example .env
```

| 변수 | 설명 |
|---|---|
| `API_KEY` | Gemini API 키 (교정/요약/키워드 추출에 사용) |
| `SPARE_KEY` | 예비 Gemini API 키 |
| `NOTION_TOKEN` | Notion Integration 토큰 |
| `NOTION_DATABASE_ID` | 결과를 업로드할 Notion 데이터베이스 ID |
| `NOTION_DATA_SOURCE_ID` | Notion API 데이터 소스 ID |
| `NOTION_PAGE_ID` | (사용처에 따라 다름 — 상위 페이지 지정용) |
| `WATCH_PATH` | 감시 대상 Google Drive 동기화 폴더 경로 (예: `G:\내 드라이브\2026-1`) |

### 3. Google Drive API 인증
`upload/google_drive.py`가 Drive 파일 링크 조회에 사용. 프로젝트 루트에 다음 파일 필요:
- `credentials.json` — Google Cloud Console에서 발급한 OAuth 클라이언트 인증 정보
- `token.pickle` — 최초 실행 시 브라우저 인증 후 자동 생성됨 (수동 생성 불필요)

두 파일 모두 `.gitignore`에 포함되어 있어 커밋되지 않음.

### 4. 폴더 준비
`WATCH_PATH` 하위에 `lecture/` 폴더를 만들고, 그 안에 강의록 PDF(줄필기/야붙)를 넣어둘 것.

## 실행 방법

```bash
python main.py
```

1. 최초 실행 시 `lecture/` 안의 `_jul`/`_yaboot` 짝을 찾아 병합 → `WATCH_PATH`에 병합 PDF 생성
2. PDF 강의자료 텍스트 및 Whisper용 키워드 프롬프트 생성
3. `colab/Transcribe.ipynb`를 Google Colab에서 열어 Google Drive 마운트 후 순서대로 셀 실행
   - mp4가 있다면 m4a로 변환
   - Whisper(`medium` 모델)로 전사 → `{base_name}_음성스크립트.txt` 생성
4. `python main.py`를 다시 실행 — 이번엔 강의자료/음성스크립트 쌍이 갖춰졌으므로 AI 교정·요약·Notion 업로드·Anki 카드 생성까지 자동으로 진행됨

## 결과물

각 강의별로 `WATCH_PATH/{base_name}/` 폴더가 생성되며 다음이 저장됨:
- `{base_name}_최종교정본.txt` — Whisper 전사를 강의록 기준으로 교정한 스크립트
- `{base_name}_result.json` — 교정본 + 요약 + 타임스탬프
- `{base_name}_scripted.pdf` — 원본 PDF에 교정 스크립트가 슬라이드별로 삽입된 문서
- Notion 페이지 업로드 (교정본 + 요약 + Drive 링크)
- Anki 카드 CSV

### 하루치 스크립트 합본 (수동)
같은 날짜의 여러 강의가 전부 `_scripted.pdf`까지 만들어졌다면, `utility/merge_pdf.py`를 직접 실행해 하루 전체를 한 파일로 합칠 수 있음:
```bash
python utility/merge_pdf.py
```
실행하면 병합할 날짜(예: `0801`)를 입력받고, `WATCH_PATH`에서 `0801_`로 시작하는 폴더들을 뒷자리 숫자 순(`0801_1`, `0801_2`, ...)으로 찾아 각 폴더의 `_scripted.pdf`를 순서대로 이어붙임. 결과는 `WATCH_PATH/merged/{날짜}_merged_scripted.pdf`로 저장됨. 대상 폴더 중 하나라도 `_scripted.pdf`가 아직 없으면 병합하지 않고 종료함 (자동 재시도 없음 — 누락 파일 확인 후 재실행 필요).

## Google Drive 폴더 예시 (여러 상태가 섞여 있는 실제 상황)

```
My Drive/                              (WATCH_PATH)
├── 0125_1.m4a                         # 녹음본만 업로드된 상태
├── 0125_2.m4a
├── 0125_2_음성스크립트.txt             # Colab 전사는 끝났지만 강의록 미업로드
├── 0125_3.pdf                         # jul+yaboot 병합까지 끝난 강의록 (아직 녹음본 없음)
├── 0125_3_강의자료.txt                # main.py가 PDF에서 추출한 텍스트
├── 0125_3_whisperkeyword.txt          # main.py가 생성한 Whisper용 키워드 프롬프트
├── 0123_1/                            # 강의자료+음성스크립트 매칭 완료 → 처리 완료 폴더
│   ├── 0123_1.pdf
│   ├── 0123_1.m4a
│   ├── 0123_1_강의자료.txt
│   ├── 0123_1_음성스크립트.txt
│   ├── 0123_1_최종교정본.txt
│   ├── 0123_1_result.json
│   └── 0123_1_scripted.pdf            # 최종 스크립트 (개별 강의 단위)
├── lecture/
│   └── 0124_1_야붙필기본.pdf           # 필기가 이미 되어 있어 병합 불필요한 원본
└── merged/
    └── 0123_merged_scripted.pdf       # merge_pdf.py로 수동 생성한 하루치 합본
```

- `_jul`/`_yaboot`로 끝나는 파일은 `lecture/`에서 자동 병합되어 루트에 결과물 생성 후 원본은 삭제됨
- `_야붙필기` 또는 `_야붙.pdf.pdf`로 끝나는 파일은 이미 필기가 합쳐진 것으로 간주되어 병합 없이 그대로 복사됨
- 강의자료(`_강의자료.txt`)와 음성스크립트(`_음성스크립트.txt`)가 모두 갖춰지면 관련 파일 전체가 `{base_name}/` 폴더로 자동 이동됨
- `merged/` 폴더와 그 안의 하루치 합본은 `merge_pdf.py`를 수동 실행해야만 생성됨 (자동 파이프라인 범위 밖)

## 참고
- `utils.py`는 `main.py`의 이전 버전으로, 현재 파이프라인에서는 사용되지 않음. 혼동 방지를 위해 정리 예정.