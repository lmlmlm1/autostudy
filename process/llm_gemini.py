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
    목적: Whisper로 추출된 [음성 스크립트]의 발음 오타를 [강의록(PDF) 텍스트]를 참고하여 교정합니다.

    [엄격한 교정 규칙]
    1. 강의록에 명시된 정확한 의학 용어를 사용하여 오타를 수정하세요.
    2. 강사가 실제로 말하지 않은 새로운 내용을 지어내거나 추가하지 마세요. (환각 금지)
    3. 강사가 말한 내용을 마음대로 요약하거나 생략하지 마세요.
    4. 영어로 된 의학 용어는 그대로 영어로 표현하고, 일반적으로 외래어로 인식되어 한국어로 쓰이는 단어들은 한글로 표현해주세요.
    5. 임상적인 기준이나 표기가 모호한 경우, 반드시 '해리슨 내과학'을 표준 기준으로 삼으세요.
    6. 원본 강의의 흐름은 그대로 유지하세요.
    7. [가장 중요] 제공된 강의록에는 '--- 1 Page ---' 와 같은 페이지 구분자가 있습니다. 음성 스크립트의 문맥을 파악하여, 반드시 해당 내용이 속하는 페이지 번호(Slide 001, Slide 002 등) 단위로 나누어 출력해야 합니다.
    8. 출력 형식이 요구될 경우 엄격히 따르세요.
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