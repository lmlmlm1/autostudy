import os
from faster_whisper import WhisperModel
from tqdm import tqdm
from moviepy import VideoFileClip

# 🚀 스피너(threading), sys, time 등 불필요한 모듈 전부 삭제!
print("🧠 [Audio 팀] Faster-Whisper AI 모델 로딩 중...")
#model = WhisperModel("large-v3-turbo", device="auto", compute_type="default")
model = WhisperModel("small", device="auto", compute_type="default")
print("✅ [Audio 팀] Whisper 준비 완료!")

def extract_and_compress_audio(video_path):
    base_path = os.path.splitext(video_path)[0]
    temp_audio_path = f"{base_path}_temp.mp3"
    
    print(f"\n🎬 영상에서 오디오 추출 및 압축 시작: {os.path.basename(video_path)}")
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(temp_audio_path, bitrate="64k", logger="bar") 
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

    try:
        segments, info = model.transcribe(target_path, beam_size=5)
        print(f"⏱️ 총 오디오 길이: 약 {int(info.duration)}초")
        
        script_text = ""
        
        # 📊 깔끔한 퍼센테이지 바만 단독으로 실행됩니다.
        with tqdm(total=info.duration, unit="초", desc="Whisper 진행률", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            for segment in segments:
                script_text += segment.text + " "
                pbar.update(segment.end - pbar.n)
        
        print(f"\n✨ 영상본/녹음본 분석 완료!")
        
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            
        return script_text.strip()

    except Exception as e:
        print(f"\n❌ 음성 추출 오류 발생: {e}")
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return None