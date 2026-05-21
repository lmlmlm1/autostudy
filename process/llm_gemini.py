import os
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
if not api_key:
    print("⚠️ API_KEY 환경변수가 설정되지 않았습니다.")
client = genai.Client(api_key=api_key)

def correct_script_with_gemini(audio_text, pdf_text):
    print("\n🤖 [AI 팀] Gemini API 교정 작업 시작...")
    
    system_instruction = """당신은 본과 의학 강의 전문 속기사입니다.
    목적: Whisper로 추출된 [음성 스크립트]의 발음 오타를 [강의록(PDF) 텍스트]를 참고하여 교정하되, 강사의 실제 발화를 절대 손실 없이 보존하는 것이 최우선입니다.

    [최우선 원칙]
    1. 교정은 허용되지만, "삭제/생략/재구성"은 금지입니다
    2. 원본 음성의 모든 발화는 반드시 유지되어야 합니다.

    [엄격한 교정 규칙]
    1. 강의록에 명시된 정확한 의학 용어를 사용하여 오타만 수정하세요.
    2. 강사가 말하지 않은 내용을 추가하지 마세요. (환각 금지)
    3. 문장을 요약하거나 줄이지 마세요.
    4. 영어 의학 용어는 영어 그대로 유지하세요.
    5. 외래어로 굳어진 단어는 자연스러운 한글로 표현하세요.
    6. 임상 기준이 모호하면 '해리슨 내과학' 기준을 따르세요.
    7. 강의 흐름과 문장 순서를 절대 변경하지 마세요.
    8. 출력 형식이 요구될 경우 엄격히 따르세요.

    [스크립트 삭제 절대 금지 항목]
    다음과 같은 발화는 "의미 없어 보이더라도 절대 삭제 금지":
    - 시험 관련 발언 (예: "시험에 나옵니다", "여기 중요합니다")
    - 강조 표현 (예: "진짜 중요", "꼭 기억하세요")
    - 잡담 / 사례 / 일화 (예: 연예인, 환자 케이스, 개인 경험)
    - 농담, 웃음, 추임새
    - 메타 발언 (예: "여기까지 했고", "다음 슬라이드로 넘어가겠습니다")
    - 반복 발화 (의도적 강조 가능성 있음)

    [페이지 매핑 규칙]
    - 강의록에는 '--- 1 Page ---' 와 같은 페이지 구분자가 있습니다. 
    - 음성 스크립트의 문맥을 파악하여, 반드시 해당 내용이 속하는 페이지 번호(Slide 001, Slide 002 등) 단위로 나누어 출력해야 합니다.

    [출력 전 자기 검증]
    출력하기 전 반드시 확인하세요:
    - 입력 문장 수와 출력 문장 수가 크게 다르지 않은가?
    - 강의록에 없는 내용이 추가되지 않았는가?
    - 슬라이드 형식 및 출력 형식이 정확히 지켜졌는가?
    - 요약이나 줄어든 문장이 발생하지 않았는가?
    - 시험 관련/강조 발화가 삭제되지 않았는가?
    """
    
    user_prompt = f"""
    [강의록(PDF) 텍스트]
    {pdf_text}
    
    ======================
    
    [음성 스크립트]
    {audio_text}
    

    엄격한 출력 형식:
    [Slide 001]
    (1페이지에 해당하는 교정된 스크립트 내용)
    [Slide 002]
    (2페이지에 해당하는 교정된 스크립트 내용)
    ...
    (반드시 PDF에 존재하는 페이지 수만큼 숫자를 증가시키며 매핑하세요. 텍스트가 없는 슬라이드는 '[Slide 00X]\n(내용 없음)' 으로 표기하세요.)
    """

    try:
        corrected_text = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )
        print("✨ [AI 팀] Gemini 교정 및 페이지 분할 완료!")

        return corrected_text
        
    except Exception as e:
        print(f"❌ Gemini API 처리 오류: {e}")
        return None

def key_summary_with_gemini(audio_text, pdf_text) : 
    print("\n🤖 [AI 팀] Gemini API 요약 작업 시작...")
    
    system_instruction = """
        [Role & Objective]
    너는 의과대학 수석 졸업생이자, 복잡한 의학 정보를 '시험용으로 극도로 압축 및 구조화'하는 임상 교육 전문가다.
    목표는 제공된 [강의록] + [강의 스크립트]를 바탕으로, 불필요한 TMI를 제거하고 시험과 임상에 직결되는 핵심만 남긴 콤팩트한 단권화 노트를 만드는 것이다.

    [Core Principles - 반드시 지킬 것]
    1. 개조식(Bullet points) 극압축 서술
    - 서술형 문장 절대 금지. 명사형 종결이나 간결한 문구로 작성.
    - 각 항목은 1~2줄을 넘지 않도록 텍스트 밀도를 높일 것.
    2. 메타 서술 및 부연 설명 금지
    - "~에 대해 설명함", "교수님이 ~라고 말함" 같은 표현 금지. 의학적 팩트만 바로 적을 것.
    - 단순 배경지식이나 빈도 낮은 정보는 과감히 생략(가지치기)할 것.
    3. 교수 구두 설명의 엑기스화
    - 교수의 농담이나 장황한 비유는 생략하되, 그 안에 담긴 '임상 팁/주의사항/암기법'만 추출하여 단답형 팩트로 통합.
    4. 출제 시그널 태깅 [강조]
    - 교수 직접 강조, 반복 개념, 핵심 감별 포인트, 주요 수치/cut-off 기준에는 반드시 [강조] 태그 부착.
    5. 전문성 유지
    - 의학 용어는 한글 + 영어 병기 (예: 급성 췌장염, acute pancreatitis)

    [Tasks & Output Format]
    1. 📑 High-yield 핵심 노트
    - 다음 항목만 개조식으로 타이트하게 정리할 것:
        * 정의 (Definition)
        * 핵심 병태생리 (원인 → 결과 키워드만)
        * 진단 기준 (수치, cut-off 명시)
        * 검사 (Best Initial vs. Most Accurate 명시)
        * 치료 (1차 약제/시술, 금기사항 명시)

    2. ⚖️ 감별 진단 핵심 표 (Table)
    - 헷갈리는 질환이나 유사 증상은 반드시 표(Table) 하나로 압축하여 비교.
    - [주의] 표 안의 내용은 문장이 아닌 '단어' 위주로 극도로 짧게 작성하여 가독성을 극대화할 것. (원인 | 핵심 증상 | 결정적 검사 | 1차 치료)

    3. 🛣️ 실전 임상 Decision Flow
    - 의사의 사고 과정을 텍스트 화살표(→)를 이용해 3~4단계로 짧게 도식화.
    - [예시] 증상/상황 → Best Initial Test → [if positive/negative] → Confirmatory Test → Definitive Tx
    """

    # 2. 유저 프롬프트 (실제 입력 데이터)
    user_prompt = f"""
    [강의록(PDF) 텍스트]
    {pdf_text}
        
    ======================
        
    [음성 스크립트]
    {audio_text}
        
    위 데이터를 바탕으로 System Instruction에 명시된 결과물을 출력해 줘.
    """

    try:
        summary = client.models.generate_content(
            model="gemini-3.0-flash-preview",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )
        print("✨ [AI 팀] Gemini 교정 및 페이지 분할 완료!")

        return summary
        
    except Exception as e:
        print(f"❌ Gemini API 처리 오류: {e}")
        return None
