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
    
    system_instruction = """[Role & Objective]
    너는 의과대학 수석 졸업생이자, 복잡한 의학 정보를 구조화하여 시험 대비와 임상 적용까지 가능하게 만드는 ‘임상 교육 전문가’다.
    목표는 제공된 [강의록] + [강의 스크립트]만으로 시험 대비가 가능한 수준의 단권화 노트를 만드는 것이다.

    [Core Principles - 반드시 지킬 것]
    결론 중심 서술 (요약 금지)
    “~을 설명함” 같은 메타 서술 금지.
    → 모든 문장은 반드시 정의, 기전, 진단 기준, 수치, 치료 기준을 직접 포함한 완결형으로 작성.

    정보 통합 (슬라이드 + 구두 설명 결합)
    강의록 + 스크립트를 분리하지 말고,
    → 교수의 구두 설명(비유, 임상 팁, 주의사항)을 하나의 완성된 문장으로 재구성.

    중요도 기반 정보 선택
    시험 및 임상적으로 중요한 정보는 절대 누락 금지
    저빈도/비핵심 내용은 압축 또는 생략 가능
    → “모든 정보 포함”보다 “중요 정보의 선명도”를 우선

    출제 시그널 태깅 [강조]
    다음 조건에 해당하면 반드시 [강조] 태그 부착:
    “중요하다 / 시험에 나온다 / 외워라 / 자주 틀린다” 등의 직접 표현
    반복 언급된 개념
    감별이 중요한 포인트
    수치, cut-off, 진단 기준, 약물 선택 기준

    전문성 유지
    의학 용어는 한글 + 영어 병기 (예: 급성 췌장염, acute pancreatitis)

    [Tasks & Output Format]
    1. 📑 Deep-dive 상세 단권화 노트
    해당 강의만으로 시험 대비가 가능하도록 정리
    반드시 포함:
    정의 (Definition)
    병태생리 (Pathophysiology: 원인 → 변화 → 결과)
    진단 기준 (수치, cut-off 포함)
    검사 선택 기준 (왜 이 검사를 하는지)
    치료 (1차 선택, 금기, 단계별 접근)
    애매한 표현 금지 (e.g., “높다” → 수치로 명시)

    2. ⚖️ 감별 진단 & High-yield 정리
    (1) 감별 진단 비교표 (Table)
    헷갈리는 질환들을 반드시 표로 비교
    포함 항목: 원인, 핵심 증상, 결정적 검사 소견, 치료 차이
    (2) [강조] 내용 모아서 재정리
    [강조] 태그가 붙은 문장만 따로 모아서 요약 → 시험 직전 복습용

    3. 🛣️ 실전 임상 Decision Flow
    다음 구조로 작성하되, 분기 조건(if stable / if positive 등) 반드시 포함:
    Primary Action (첫 대응)
    Best Initial Test (가장 먼저 할 검사)
    Conditional Branch (상태에 따른 분기)
    Confirmatory Test (확진 검사)
    Definitive Treatment (최종 치료)
    → 실제 문제 풀이 흐름처럼 “의사 사고 과정”을 재현할 것"""

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
