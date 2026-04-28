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

def generate_anki_csv(lecture_text, script_text):
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
- 작성 규칙: Anki의 Cloze 문법인 {{c1::정답}}, {{c2::정답}}을 정확히 사용하라. 연관된 개념을 한 번에 외워야 하면 같은 번호 {{c1::A}}와 {{c1::B}}를 쓰고, 따로 외워야 하면 번호를 나누어라.
- 필드 구성: '필드1'에는 빈칸이 뚫린 전체 문장을, '필드2'에는 보충 해설을 적어라.
- 출력 예시: Cloze|대동맥판 협착증(AS)의 3대 증상은 {{c1::Syncope}}, {{c2::Angina}}, {{c3::Dyspnea}} 이다.|해설: 운동 시 심박출량 증가의 제한 때문임.|#순환기 #판막질환 #증상

▶ Type 3: MCQ (5지선다형 객관식)
- 적합한 내용: 학습을 시험하는 시험에 낼 만한 문제들과 임상 활용 문제들
- 출력 예시: MCQ|문제 내용<br><br>1) 보기1<br>2) 보기2...|<b>정답: 3번</b><br><br>해설: (명확한 근거)|#객관식 #임상

[강의록 텍스트]
{lecture_text}
[강의 스크립트]
{script_text}
"""

    try:
        # 복잡한 논리 구조 처리를 위해 2.5-pro 모델 사용
        response = client.models.generate_content(
            model="gemini-2.5-pro", 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1 # 지어내기 방지를 위한 보수적 설정
            )
        )
        
        csv_result = response.text.replace("```csv", "").replace("```", "").strip()
        print("✨ [Anki 팀] 카드 생성 완료!")
        return csv_result
        
    except Exception as e:
        print(f"❌ Anki 카드 생성 오류: {e}")
        return None

def save_anki_file(csv_data, base_name, target_dir):
    if not csv_data:
        return
    
    lines = csv_data.strip().split('\n')
    
    # 3개 파일로 분리하기 위한 리스트 준비
    basic_lines = []
    mcq_lines = []
    cloze_lines = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
            
        if line.startswith("Basic"):
            basic_lines.append(line)
        elif line.startswith("MCQ"):
            mcq_lines.append(line)
        elif line.startswith("Cloze"):
            cloze_lines.append(line)
        else:
            basic_lines.append(line) # 타입 불명확 시 기본으로 포함
            
    # 각각의 파일로 저장 (한글 깨짐 방지 utf-8-sig)
    save_info = [
        (basic_lines, "Basic"),
        (mcq_lines, "MCQ"),
        (cloze_lines, "Cloze")
    ]
    
    for data_list, suffix in save_info:
        if data_list:
            file_path = os.path.join(target_dir, f"{base_name}_{suffix}.csv")
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write('\n'.join(data_list))
            print(f"💾 [Anki 팀] {suffix} 파일 저장 완료: {os.path.basename(file_path)}")

    print(f"✅ 모든 Anki 파일 분리 저장이 완료되었습니다.")