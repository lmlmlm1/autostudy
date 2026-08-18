import os
import yt_dlp
from dotenv import load_dotenv
load_dotenv()
WATCH_PATH = os.environ.get("WATCH_PATH")

def download_lossless_audio(video_url, watch_path, prefix):
    """
    yt-dlp를 사용하여 다운로드 후 Whisper AI에 최적화된 M4A(16kHz, Mono) 포맷으로 추출합니다.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(watch_path, f'{prefix}.%(ext)s'),
        'cookiefile': 'cookies.txt', 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',  # 👈 wav에서 m4a로 변경
        }],
        'postprocessor_args': {
            # 👈 pcm_s16le(WAV 무손실 코덱) 부분을 제거합니다.
            # M4A의 기본 코덱(aac)이 자동 적용되며, Whisper 최적화용 샘플링레이트(16kHz)와 채널(Mono)만 유지합니다.
            'ffmpeg': ['-ar', '16000', '-ac', '1'] 
        },
        'quiet': False,
        'no_warnings': True
    }

    print(f"다운로드 및 오디오 변환 시작: {video_url}")
    
    # yt-dlp 객체 생성 및 다운로드 실행
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"완료! 저장 위치: {os.path.join(watch_path, f'{prefix}.m4a')}") # 👈 출력 메시지도 m4a로 변경
    except Exception as e:
        print(f"에러가 발생했습니다: {e}")

# --- 실행 예시 ---
if __name__ == "__main__":
    target_url = "https://youtu.be/IffCAv0Voz0?list=PLIMKdiHIXXD4"
    download_folder = WATCH_PATH
    file_prefix = "0812_1"

    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        
    download_lossless_audio(target_url, download_folder, file_prefix)