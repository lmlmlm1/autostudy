# AutoStudy 초보자용 시작 안내

> **이 폴더는 VS Code나 터미널을 사용하지 않는 사용자를 위한 공간입니다.** 강의록 PDF와 녹음 파일을 정리하면, 전사문·시험 대비 노트·Anki 카드·Notion 페이지·복습용 PDF를 만드는 Windows용 개인 학습 도우미입니다.

AutoStudy는 **Windows에서만 사용**하도록 구성되어 있습니다. VS Code나 터미널을 사용할 필요가 없습니다. 이 `chobo` 폴더를 벗어나지 말고, 처음에는 `설치하기.cmd`와 `설정_변경하기.cmd`를 각각 한 번 실행한 뒤 이후에는 `AutoStudy_실행.cmd`를 더블클릭하면 됩니다.

| 처음 할 일 | 언제 하나요? | 누르는 파일 |
|---|---:|---|
| 프로그램 설치 | 한 번만 | `설치하기.cmd` |
| 작업 폴더·Gemini·Notion·Drive 연결 | 한 번만 또는 설정 변경 시 | `설정_변경하기.cmd` |
| 강의 처리 | 강의마다 두 번 | `AutoStudy_실행.cmd` |
| 여러 강의의 복습 PDF 합치기 | 하루 강의가 끝난 뒤 | `오늘_복습PDF_합치기.cmd` |

## 시작 순서

처음 받은 분은 **반드시 [`처음_설정하기.md`](./처음_설정하기.md)를 먼저 읽으세요.** 작업 폴더(`WATCH_PATH`)와 Gemini API 키가 설정되지 않으면 프로그램은 실행할 수 없습니다. 설치가 완료된 뒤에는 [`사용법.md`](./사용법.md)의 순서만 따르면 됩니다.

> **중요:** API 키, Notion 토큰, `credentials.json`, `token.pickle`, `.env` 파일은 비밀번호와 같은 정보입니다. 다른 사람에게 보내거나 GitHub·단체 채팅방에 올리지 마세요. Gemini API 키가 노출되면 제3자가 사용량을 발생시킬 수 있으므로 즉시 새 키로 교체해야 합니다.[1]

## 한 강의를 처리하는 흐름

강의마다 프로그램은 같은 작업을 두 번 수행합니다. 첫 실행은 PDF를 읽어 의학용어 키워드를 만들고, 그다음 Google Colab이 녹음을 전사합니다. 전사문이 생긴 뒤 두 번째 실행을 하면 교정·요약·Notion·Anki·복습 PDF가 생성됩니다.

| 순서 | 사용자가 하는 일 | 만들어지는 주요 결과 |
|---:|---|---|
| 1 | 작업 폴더에 강의 자료와 녹음 파일을 넣습니다. | 입력 파일 준비 |
| 2 | `AutoStudy_실행.cmd`를 더블클릭합니다. | `_강의자료.txt`, `_whisperkeyword.txt` |
| 3 | Colab 노트북을 위에서 아래로 실행합니다. | `_음성스크립트.txt` |
| 4 | `AutoStudy_실행.cmd`를 다시 더블클릭합니다. | 최종교정본, Notion, Anki, 복습 PDF |

파일 이름의 앞부분이 같아야 같은 강의로 인식됩니다. 예를 들어 `0123_1.pdf`와 `0123_1.m4a`는 한 강의로 처리되지만, `0123_1.pdf`와 `0123-1.m4a`는 서로 다른 파일로 인식됩니다.

## 필요한 프로그램과 계정

| 항목 | 용도 | 필요 여부 |
|---|---|---:|
| Windows 10 또는 11 PC | AutoStudy 실행 환경 | 필수 |
| Python 3.11 권장 | AutoStudy 프로그램 실행 | 필수 |
| Google Drive for desktop | PC 작업 폴더와 Colab·Drive 링크 동기화 | 필수 |
| Google 계정 및 Gemini API 키 | 키워드 생성·교정·요약·Anki 카드 생성 | 필수 |
| Notion 계정과 빈 데이터베이스 | 핵심 요약과 스크립트 보관 | 필수 |
| Google Cloud OAuth `credentials.json` | Notion에 Drive 파일 링크를 넣기 위한 최초 인증 | 필수 |
| Anki | 생성된 `.apkg` 암기 카드 파일 열기 | 권장 |
| Tesseract OCR | 글자가 이미지로만 된 스캔 PDF 읽기 | 해당할 때만 |

## 문서 안내

| 문서 | 대상 | 내용 |
|---|---|---|
| [`처음_설정하기.md`](./처음_설정하기.md) | 처음 설치하는 사용자 또는 설정을 도와주는 사람 | 설치, `WATCH_PATH`, Gemini API, Notion, Google Drive OAuth, 문제 점검 |
| [`사용법.md`](./사용법.md) | 매일 사용하는 사용자 | 자료 넣기, 두 번 실행하기, Colab 전사, 결과 확인, 합본 만들기 |
| [`../DEVELOPMENT.md`](../DEVELOPMENT.md) | 개발·관리 담당자 | 코드 구조와 구현 세부사항 |

## 개인정보와 강의 자료

이 프로그램은 PDF와 전사문 내용을 Gemini API로 보내 교정·요약·카드 생성을 수행하고, 결과를 사용자가 설정한 Notion과 Google Drive에 저장합니다. 환자 실명, 등록번호, 연락처 등 개인을 식별할 수 있는 정보가 녹음 또는 자료에 포함되어 있다면 업로드 전에 삭제하거나 비식별화하세요. 강의 자료의 저작권과 학교·병원 내부 규정도 사용자가 확인해야 합니다.

## 도움을 요청할 때

문제가 생겼다면 파일을 바로 지우지 말고, `AutoStudy_실행.cmd` 창의 오류 문구 전체와 작업 폴더 화면을 캡처하세요. 아래 정보까지 함께 전달하면 원인 확인이 빨라집니다.

| 전달할 정보 | 예시 |
|---|---|
| 문제가 난 단계 | 첫 실행, Colab 전사, 두 번째 실행, Notion 업로드 |
| 처리하려던 파일 이름 | `0123_1.pdf`, `0123_1.m4a` |
| 작업 폴더 위치 | `G:\내 드라이브\AutoStudy` |
| 오류 화면 | 창 전체가 보이는 캡처 |

## References

[1] [Google AI for Developers, *Using Gemini API keys*](https://ai.google.dev/gemini-api/docs/api-key)
[2] [Google Workspace Developers, *Create access credentials*](https://developers.google.com/workspace/guides/create-credentials)
[3] [Notion Developers, *Working with databases*](https://developers.notion.com/guides/data-apis/working-with-databases)
