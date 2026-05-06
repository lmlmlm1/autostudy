import os
import mlx_whisper
from moviepy import VideoFileClip
from google import genai

print("🧠 [Audio 팀] MLX-Whisper AI 준비 중 (Apple Silicon 최적화)...")

# 메인에서 이미 load_dotenv()를 했으므로 바로 가져옵니다.
api_key = os.getenv("API_KEY")
if not api_key:
    print("⚠️ 오류: API_KEY를 찾을 수 없습니다!")
client = genai.Client(api_key=api_key)

def get_dynamic_prompt(audio_file_path):
    base_path = os.path.splitext(audio_file_path)[0]
    txt_path = f"{base_path}_강의자료.txt"
    
    if not os.path.exists(txt_path):
        return None

    print(f"🧠 [Gemini API] 강의자료에서 핵심 의학 용어 추출 중... ({os.path.basename(txt_path)})")
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read() # 토큰 제한이 넉넉하므로 통째로 읽습니다.

        query = f"""
        다음은 의과대학 전공 강의록입니다. Whisper AI가 이 강의의 음성을 정확하게 인식할 수 있도록,
        가장 발음이 헷갈리기 쉽거나 중요한 핵심 전문 용어(해부학, 질병명, 약물, 기호 등)를 딱 30개만 추출해주세요.
        조건: 다른 부연 설명 없이, 오직 추출된 용어들만 쉼표(,)로 연결해서 출력하세요.
        
        강의록 내용:
        {content}
        """
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=query
        )
        keywords = response.text.strip()
        
        final_prompt = f"다음은 의학 전공 강의입니다. 전문 용어에 주의하세요: {keywords}"
        # Whisper initial_prompt 길이 제한 방어 (안전하게 400자로 컷)
        if len(final_prompt) > 400:
            final_prompt = final_prompt[:397] + "..."
            
        return final_prompt
        
    except Exception as e:
        print(f"❌ Gemini 프롬프트 추출 오류: {e}")
        return None

def extract_and_compress_audio(video_path):
    base_path = os.path.splitext(video_path)[0]
    temp_audio_path = f"{base_path}_temp.wav"
    
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(
        temp_audio_path,
        fps=16000, nbytes=2, codec='pcm_s16le', ffmpeg_params=["-ac", "1"], logger=None
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

    dynamic_initial_prompt = get_dynamic_prompt(file_path)

    try:
        transcribe_args = {
            "path_or_hf_repo": "mlx-community/whisper-large-v3-turbo",
            "language": "ko",
            "verbose": False,
            "condition_on_previous_text": False,
            "no_speech_threshold": 0.55,
            "compression_ratio_threshold": 2.3,
            "temperature": (0.0, 0.2, 0.4)
        }
        if dynamic_initial_prompt:
            transcribe_args["initial_prompt"] = dynamic_initial_prompt

        result = mlx_whisper.transcribe(target_path, **transcribe_args)
        script_text = result["text"].strip()
        
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            
        return script_text

    except Exception as e:
        print(f"\n❌ 음성 추출 오류 발생: {e}")
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return None