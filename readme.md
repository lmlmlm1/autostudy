# AutoStudy

> 의과대학 강의의 PDF 강의록과 음성 녹음을 바탕으로 전사문, 시험 대비 노트, Anki 카드, Notion 정리, 복습용 PDF를 만드는 개인용 학습 파이프라인입니다.

이 저장소는 **두 종류의 사용자를 분명하게 구분**합니다. 본인이 VS Code·터미널·환경 변수·API 설정을 사용해 본 적이 없다면 기술 문서를 읽지 말고 `chobo` 폴더부터 여세요. 반대로 코드를 수정하거나 설치·연동 문제를 관리할 사람이라면 `DEVELOPMENT.md`를 읽으세요.

| 나는 누구인가요? | 먼저 열 파일 | 다음 행동 |
|---|---|---|
| 처음 설치하는 일반 사용자 | [`chobo/README.md`](./chobo/README.md) | 안내에 따라 `chobo` 폴더 안의 파일만 실행합니다. |
| API·Notion·Google Drive 설정을 대신 해 주는 사람 | [`DEVELOPMENT.md`](./DEVELOPMENT.md) | 구현 구조와 환경 변수, 연동 요구사항을 확인합니다. |
| 코드를 수정하거나 오류를 분석하는 개발자 | [`DEVELOPMENT.md`](./DEVELOPMENT.md) | 기술 문서와 소스 코드를 함께 확인합니다. |

> **초보 사용자 안내:** `chobo` 폴더를 열어 `README.md`에 적힌 순서대로만 진행하세요. 프로그램의 나머지 Python 파일이나 환경 설정 파일을 직접 열고 수정할 필요가 없습니다.

## 프로젝트 구조

```text
.
├── chobo/                 # 비개발자용 안내·설정·실행 파일
│   ├── README.md
│   ├── 처음_설정하기.md
│   ├── 사용법.md
│   ├── 설치하기.cmd
│   ├── 설정_변경하기.cmd
│   ├── AutoStudy_실행.cmd
│   ├── 오늘_복습PDF_합치기.cmd
│   └── 처음_설정하기.py
├── DEVELOPMENT.md         # 개발·관리 담당자용 기술 문서
├── main.py                # 처리 진입점
├── colab/Transcribe.ipynb # 음성 전사 노트북
├── process/               # Gemini·Notion·Anki 처리 모듈
├── utility/               # PDF 병합 등 보조 기능
├── env.example            # 환경 변수 형식 예시
└── requirements.txt       # Python 의존성 목록
```

## 보안과 개인정보

`.env`, `credentials.json`, `token.pickle`에는 API 키·OAuth 인증 정보가 들어갈 수 있습니다. 이 파일들은 GitHub, 메신저, 팀 드라이브에 업로드하거나 다른 사람에게 전달하지 마세요. Gemini API 키가 노출되면 제3자가 사용량을 발생시킬 수 있으므로, 노출이 의심되면 해당 키를 교체해야 합니다.[1]

강의 자료나 녹음에 환자 실명, 등록번호, 연락처처럼 개인을 식별할 수 있는 정보가 포함되어 있다면 외부 서비스로 보내기 전에 비식별화해야 합니다. 학교·병원 규정과 강의 자료의 저작권 준수도 사용자의 책임입니다.

## References

[1] [Google AI for Developers, *Using Gemini API keys*](https://ai.google.dev/gemini-api/docs/api-key)
