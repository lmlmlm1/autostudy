import os
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv

# 🎯 환경변수 로드 및 클라이언트 설정
load_dotenv()
api_key = os.getenv("API_KEY")
if not api_key:
    print("⚠️ API_KEY 환경변수가 설정되지 않았습니다. .env 파일이나 시스템 환경변수를 확인해주세요.")
client = genai.Client(api_key=api_key)

def generate_anki_csv(lecture_text):
    print("\n🗂️ [Anki 팀] 튜터 AI가 복습용 Anki 카드를 생성 중입니다...")
    
    prompt = f"""너는 의대생의 학습을 돕는 최고 수준의 의학 튜터야. 내가 제공하는 [강의록 텍스트]를 바탕으로, 복습 및 암기를 위한 Anki 카드를 생성해 줘.

[절대 규칙 - 엄수할 것]
1. 내용의 출처: 철저하게 [강의록 텍스트]를 1순위 기준으로 삼아라. 일반적인 의학 지식(해리슨 등)과 강의록 내용이 충돌할 경우, 무조건 강의록을 우선시해라.
2. 환각 금지: 강의록에 없는 외부 지식을 임의로 덧붙이거나 지어내지 마라.
3. 출력 포맷: 무조건 파이프(|) 기호로 구분된 4열 CSV 포맷으로 출력하라. (형식: 카드타입|필드1(질문/빈칸본문)|필드2(정답/해설)|태그)
4. 텍스트 내 파이프(|) 기호 사용 절대 금지: 내용 안에 파이프 기호가 들어가면 시스템이 고장난다. 줄바꿈은 <br><br>를 사용하라.
5. 포맷팅: 강조할 핵심 키워드는 <b>키워드</b> 또는 **키워드**로 볼드 처리하라.
6. [이미지 처리]: 해부학적 위치, 영상의학적 소견(CT, X-ray, 심전도), 슬라이드 표 등 시각적 자료가 필요한 경우, 필드1이나 필드2의 적절한 위치에 `[이미지 삽입 필요: (어떤 이미지인지 구체적인 설명)]` 태그를 삽입하라.
7. 불필요한 말 금지: 인사말이나 설명 없이 오직 CSV 데이터만 출력하라.

[카드 생성 가이드라인]
AI인 네가 판단하여, 텍스트의 성격에 따라 아래 3가지 타입 중 가장 암기하기 좋은 형태를 스스로 선택해서 카드를 만들어라. 

▶ Type 1: Basic (일반 Q&A)
- 적합한 내용: 명확한 정의, 1차 치료제, 특징적인 단일 증상 등 1:1 매칭이 좋은 개념.
- 출력 예시: Basic|OOO의 가장 흔한 원인균은?|<b>정답: 폐렴구균</b><br><br>해설: (필요시 짧은 해설)|#호흡기 #원인균

▶ Type 2: Cloze (빈칸 뚫기)
- 적합한 내용: 3가지 이상의 진단 기준, 생리학적 기전(A → B → C), 여러 특징이 나열된 문장 등.
- 작성 규칙: Anki의 Cloze 문법인 {{{{c1::정답}}}}, {{{{c2::정답}}}}을 정확히 사용하라. 연관된 개념을 한 번에 외워야 하면 같은 번호 {{{{c1::A}}}}와 {{{{c1::B}}}}를 쓰고, 따로 외워야 하면 번호를 나누어라.
- 필드 구성: '필드1'에는 빈칸이 뚫린 전체 문장을, '필드2'에는 보충 해설을 적어라.
- 출력 예시: Cloze|대동맥판 협착증(AS)의 3대 증상은 {{{{c1::Syncope}}}}, {{{{c2::Angina}}}}, {{{{c3::Dyspnea}}}} 이다.|해설: 운동 시 심박출량 증가의 제한 때문임.|#순환기 #판막질환 #증상

▶ Type 3: MCQ (5지선다형 객관식)
- 적합한 내용: 임상 시나리오 문제, 헷갈리기 쉬운 감별 진단.
- 출력 예시: MCQ|문제 내용<br><br>1) 보기1<br>2) 보기2...|<b>정답: 3번</b><br><br>해설: (명확한 근거)|#객관식 #임상

[강의록 텍스트]
{lecture_text}
"""

    try:
        # 복잡한 논리 구조(Cloze 파싱 등)를 완벽하게 수행하기 위해 2.5-pro 모델 사용
        response = client.models.generate_content(
            model="gemini-2.5-pro", 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1 # 환각(지어내기) 방지를 위해 아주 낮게 설정
            )
        )
        
        # AI가 코드 블록(```csv ... ```)으로 텍스트를 감싸서 대답할 경우를 대비한 클렌징 작업
        csv_result = response.text.replace("```csv", "").replace("```", "").strip()
        print("✨ [Anki 팀] 카드 생성 완료!")
        
        return csv_result
        
    except Exception as e:
        print(f"❌ Anki 카드 생성 오류: {e}")
        return None


def save_anki_file(csv_data, base_name, target_dir):
    if not csv_data:
        return
    
    # 1. 텍스트를 줄 단위로 쪼개기
    lines = csv_data.strip().split('\n')
    
    basic_mcq_lines = []
    cloze_lines = []
    
    # 2. 첫 번째 열(카드 타입)을 보고 배열 분류하기
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("Basic") or line.startswith("MCQ"):
            basic_mcq_lines.append(line)
        elif line.startswith("Cloze"):
            cloze_lines.append(line)
        else:
            # 예외: 만약 타입 명시가 빠진 줄이 있다면 유실 방지를 위해 기본 덱에 포함
            basic_mcq_lines.append(line)
            
    # 3. 파일 두 개로 나누어서 저장! (한글 깨짐 방지 utf-8-sig 적용)
    if basic_mcq_lines:
        basic_path = os.path.join(target_dir, f"{base_name}_Basic_MCQ.csv")
        with open(basic_path, "w", encoding="utf-8-sig") as f:
            f.write('\n'.join(basic_mcq_lines))
            
    if cloze_lines:
        cloze_path = os.path.join(target_dir, f"{base_name}_Cloze.csv")
        with open(cloze_path, "w", encoding="utf-8-sig") as f:
            f.write('\n'.join(cloze_lines))
            
    print(f"💾 [Anki 팀] 파일 분리 저장 완료! (추출된 카드 종류에 따라 해당 폴더에 CSV 파일이 생성되었습니다.)")