import os
import mlx_whisper
from moviepy import VideoFileClip
import google.generativeai as genai
from dotenv import load_dotenv  # 추가된 부분

print("🧠 [Audio 팀] MLX-Whisper AI 준비 중 (Apple Silicon 최적화)...")

# 1. 같은 폴더에 있는 .env 파일을 읽어서 환경변수로 등록
load_dotenv() 

# 2. .env에서 읽어온 API_KEY 가져오기
api_key = os.getenv("API_KEY")

# 3. Gemini에 API 키 세팅하기 (이 줄이 반드시 있어야 작동해!)
if api_key:
    genai.configure(api_key=api_key)
else:
    print("⚠️ 오류: .env 파일에서 API_KEY를 찾을 수 없습니다!")

def get_dynamic_prompt(audio_file_path):
    
    """
    동일한 폴더에 있는 '{파일명}_강의자료.txt'를 찾아 
    Gemini를 통해 핵심 의학 용어를 추출합니다.
    """
    # 원본 파일명에서 확장자를 제외한 이름 추출 (예: '심장학_1강.mp4' -> '심장학_1강')
    base_path = os.path.splitext(audio_file_path)[0]
    txt_path = f"{base_path}_강의자료.txt"
    
    if not os.path.exists(txt_path):
        print(f"⚠️ [Prompt] 강의자료 텍스트 파일을 찾을 수 없습니다: {os.path.basename(txt_path)}")
        print("   -> 💡 기본 설정(프롬프트 없이)으로 전사를 진행합니다.")
        return None

    print(f"🧠 [Gemini API] 강의자료 읽는 중... ({os.path.basename(txt_path)})")
    try:
        # 모델 설정 (속도가 빠른 flash 모델 권장)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # 텍스트 파일 읽기 (전체 내용이 너무 길면 앞부분 5000자만 읽어 토큰 절약)
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read(5000) 

        # 의학 용어 추출 프롬프트
        query = f"""
        다음은 의과대학 전공 강의록입니다. Whisper AI가 이 강의의 음성을 정확하게 인식할 수 있도록,
        핵심 전문 용어(해부학 명칭, 질병명, 검사법 기호 등)를 20~30개 내외로 추출해주세요.
        영어와 한글을 섞어서, 쉼표로만 구분된 하나의 문자열로 반환해주세요.
        (예시: Coronary artery, 심전도, ECG, LAO view, 폐아스페르길루스증, sequestration)
        
        강의록 내용:
        {content}
        """
        response = model.generate_content(query)
        keywords = response.text.strip()
        
        print(f"✅ [키워드 추출 완료] {keywords[:100]}... (이하 생략)")
        
        # Whisper에게 전달할 최종 프롬프트 문장
        final_prompt = f"다음은 의과대학 전공 강의입니다. 전문 용어에 주의해서 정확하게 전사하세요. 포함된 용어: {keywords}"
        return final_prompt
        
    except Exception as e:
        print(f"❌ Gemini API 호출 중 오류 발생: {e}")
        print("   -> 💡 기본 설정으로 전사를 진행합니다.")
        return None

def extract_and_compress_audio(video_path):
    base_path = os.path.splitext(video_path)[0]
    temp_audio_path = f"{base_path}_temp.wav"
    
    print(f"\n🎬 영상에서 오디오 추출 시작 (WAV 포맷 최적화): {os.path.basename(video_path)}")
    video = VideoFileClip(video_path)
    
    video.audio.write_audiofile(
        temp_audio_path,
        fps=16000,              
        nbytes=2,               
        codec='pcm_s16le',      
        ffmpeg_params=["-ac", "1"], 
        logger="bar"
    )
    video.close()
    return temp_audio_path


def extract_text_from_audio(file_path):
    print(f"\n🎙️ 스크립트 추출을 시작합니다... (대상: {os.path.basename(file_path)})")

    extension = os.path.splitext(file_path)[1].lower()
    temp_file = None
    if extension == '.mp4':
        temp_file = extract_and_compress_audio(file_path)
        target_path = temp_file
    else:
        target_path = file_path

    # --- 추가된 부분: Gemini를 통해 동적 프롬프트 생성 ---
    dynamic_initial_prompt = get_dynamic_prompt(file_path)

    try:
        print("\n⏳ MLX-Whisper가 음성을 텍스트로 변환 중입니다. (Apple GPU/NPU 풀가동 🚀)")
        
        # Whisper 파라미터 기본 세팅 (환각 방지 옵션 포함)
        transcribe_args = {
            "path_or_hf_repo": "mlx-community/whisper-large-v3-turbo",
            "language": "ko",
            "verbose": True,
            "condition_on_previous_text": False, # 무한 루프 차단
            "no_speech_threshold": 0.55,         # 무음 필터 강화
            "compression_ratio_threshold": 2.3,  # 반복 텍스트 차단
            "temperature": (0.0, 0.2, 0.4)       # 소설 쓰기(환각) 억제
        }
        
        # Gemini가 프롬프트를 성공적으로 만들어냈다면 kwargs에 추가
        if dynamic_initial_prompt:
            transcribe_args["initial_prompt"] = dynamic_initial_prompt

        # 언패킹(**) 연산자를 사용해 파라미터 전달
        result = mlx_whisper.transcribe(target_path, **transcribe_args)
        
        script_text = result["text"].strip()
        
        print(f"\n✨ 영상본/녹음본 분석 완료!")
        
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            
        return script_text

    except Exception as e:
        print(f"\n❌ 음성 추출 오류 발생: {e}")
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return None

# — 실행 예시 —
# text_result = extract_text_from_audio("/경로/호흡기학_4주차.mp4")
# print(text_result)