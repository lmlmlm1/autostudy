import os
import mlx_whisper
from moviepy import VideoFileClip

print("🧠 [Audio 팀] MLX-Whisper AI 준비 중 (Apple Silicon 최적화)...")
# MLX는 최초 transcribe 호출 시 모델을 로드하고 캐싱합니다.

def extract_and_compress_audio(video_path):
    base_path = os.path.splitext(video_path)[0]
    # MP3 대신 비압축 WAV 포맷 사용
    temp_audio_path = f"{base_path}_temp.wav"
    
    print(f"\n🎬 영상에서 오디오 추출 시작 (WAV 포맷 최적화): {os.path.basename(video_path)}")
    video = VideoFileClip(video_path)
    
    # Whisper 최적화 파라미터: 16kHz, 16bit, Mono(단일 채널)
    video.audio.write_audiofile(
        temp_audio_path,
        fps=16000,              # 16kHz 샘플링 레이트
        nbytes=2,               # 16bit 오디오
        codec='pcm_s16le',      # 비압축 PCM 코덱
        ffmpeg_params=["-ac", "1"], # 모노(Mono) 채널로 병합
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

    try:
        print("⏳ MLX-Whisper가 음성을 텍스트로 변환 중입니다. (Apple GPU/NPU 풀가동 🚀)")
        
        # mlx-whisper는 허깅페이스의 mlx-community 모델을 바로 다운로드/사용합니다.
        # verbose=True를 주면 faster_whisper의 진행률 바 대신 실시간 변환 텍스트가 콘솔에 찍힙니다.
        result = mlx_whisper.transcribe(
            target_path,
            path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
            verbose=True
        )
        
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
