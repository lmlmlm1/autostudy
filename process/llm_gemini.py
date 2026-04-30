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
    (강의 핵심 내용 및 중요한 내용들 요약)
    [SEPARATOR] 
    (중요 용어와 설명)
    [SEPARATOR]
    [Slide 001]
    (1페이지에 해당하는 교정된 스크립트 내용)
    [Slide 002]
    (2페이지에 해당하는 교정된 스크립트 내용)
    ...
    (반드시 PDF에 존재하는 페이지 수만큼 숫자를 증가시키며 매핑하세요. 텍스트가 없는 슬라이드는 '[Slide 00X]\n(내용 없음)' 으로 표기하세요.)
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )

        parts = response.text.split("[SEPARATOR]")
        summary = parts[0].strip() if len(parts) > 0 else ""
        terms = parts[1].strip() if len(parts) > 1 else "용어 정리 실패"
        corrected_text = parts[2].strip() if len(parts) > 2 else "스크립트 교정 실패"
        
        print("✨ [AI 팀] Gemini 교정 및 페이지 분할 완료!")

        return summary, terms, corrected_text
        
    except Exception as e:
        print(f"❌ Gemini API 처리 오류: {e}")
        return None, None, None