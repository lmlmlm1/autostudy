import os
import mlx_whisper
from moviepy import VideoFileClip
from google import genai
from pydub import AudioSegment, silence

print("🧠 [Audio 팀] MLX-Whisper AI 준비 중 (M4 최적화)...")

api_key = os.getenv("API_KEY")
client = genai.Client(api_key=api_key)

def get_dynamic_prompt(audio_file_path):
    base_path = os.path.splitext(audio_file_path)[0]
    txt_path = f"{base_path}_강의자료.txt"
    if not os.path.exists(txt_path): return None
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 키워드를 20개로 줄여 토큰 최적화
        query = f"다음 의학 강의록에서 핵심 전문 용어 20개만 쉼표로 연결해 추출하세요:\n{content}"
        response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=query)
        keywords = response.text.strip()
        
        # [핵심 수정 1] 지시문이 아닌 자연스러운 문맥 형태로 프롬프트 변경
        # [핵심 수정 2] 토큰 초과 방지를 위해 200자 제한으로 축소
        final_prompt = f"의학 강의 키워드: {keywords}."
        return final_prompt[:200]
        
    except Exception as e: 
        print(f"⚠️ 프롬프트 생성 실패: {e}")
        return None

def extract_and_compress_audio(video_path):
    base_path = os.path.splitext(video_path)[0]
    temp_audio_path = f"{base_path}_temp.wav"
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(temp_audio_path, fps=16000, nbytes=2, codec='pcm_s16le', ffmpeg_params=["-ac", "1"], logger=None)
    video.close()
    return temp_audio_path

def apply_vad_preprocessing(audio_path):
    """적응형 임계값을 사용하여 음성 유실을 방지합니다."""
    print("✂️ [VAD] 오디오 분석 및 침묵 제거 시작...")
    audio = AudioSegment.from_file(audio_path)
    
    orig_duration = len(audio) / 1000.0
    
    # 평균 볼륨보다 16dB 낮은 소리부터 침묵으로 간주
    adaptive_thresh = audio.dBFS - 16 
    print(f"📊 오디오 평균 볼륨: {audio.dBFS:.2f}dB | 설정된 임계값: {adaptive_thresh:.2f}dB")

    # 강의 특성상 2초(2000ms) 이상의 정적만 제거
    chunks = silence.split_on_silence(
        audio, 
        min_silence_len=2000, 
        silence_thresh=adaptive_thresh, 
        keep_silence=500  # 단어 앞뒤 0.5초 여유
    )
    
    if not chunks:
        print("⚠️ 침묵으로 판단된 구간이 없습니다. 원본을 사용합니다.")
        return audio_path
    
    combined = AudioSegment.empty()
    for chunk in chunks:
        combined += chunk
    
    new_duration = len(combined) / 1000.0
    print(f"✅ VAD 결과: {orig_duration:.1f}초 -> {new_duration:.1f}초 (약 {orig_duration - new_duration:.1f}초 제거됨)")
    
    if new_duration < orig_duration * 0.2:
        print("🚨 경고: 오디오의 80% 이상이 삭제되었습니다! 임계값을 확인하세요.")

    vad_path = audio_path.replace(".wav", "_cleaned.wav")
    combined.export(vad_path, format="wav")
    return vad_path

def extract_text_from_audio(file_path):
    print(f"\n🎙️ 스크립트 추출 시작: {os.path.basename(file_path)}")
    extension = os.path.splitext(file_path)[1].lower()
    temp_files = []
    
    if extension == '.mp4':
        target_path = extract_and_compress_audio(file_path)
        temp_files.append(target_path)
    else:
        target_path = file_path

    # 적응형 VAD 적용
    cleaned_path = apply_vad_preprocessing(target_path)
    if cleaned_path != target_path:
        temp_files.append(cleaned_path)
    
    dynamic_initial_prompt = get_dynamic_prompt(file_path)

    try:
        # [핵심 수정 3] 루핑 방지를 위한 Whisper 파라미터 튜닝
        transcribe_args = {
            "path_or_hf_repo": "mlx-community/whisper-large-v2-mlx",
            "language": "ko",
            "verbose": False,
            "condition_on_previous_text": False,          # 루프 전염 방지
            "no_speech_threshold": 0.6,
            "compression_ratio_threshold": 2.0,           # (수정) 2.4 -> 2.0으로 하향 조정하여 루핑 조기 차단
            "logprob_threshold": -1.0,                    # (추가) 확률이 낮은 엉뚱한 예측 차단
            "temperature": (0.0, 0.1, 0.2, 0.4, 0.6, 0.8) # (수정) 재시도 온도를 세밀하게 조정
        }
        
        if dynamic_initial_prompt:
            transcribe_args["initial_prompt"] = dynamic_initial_prompt

        result = mlx_whisper.transcribe(cleaned_path, **transcribe_args)
        script_text = result["text"].strip()
        
        # 임시 파일 정리
        for f in temp_files:
            if os.path.exists(f): os.remove(f)
                
        return script_text

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        # 오류 발생 시에도 임시 파일은 정리
        for f in temp_files:
            if os.path.exists(f): os.remove(f)
        return None