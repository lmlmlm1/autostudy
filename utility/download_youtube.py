#반드시 Target URL을 si=?의 주소를 사용할 것

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
        'noplaylist': True,
        'outtmpl': os.path.join(watch_path, f'{prefix}.%(ext)s'),
        'cookiefile': 'cookies.txt',
        # 로그인 쿠키 사용 시 문제를 일으키는 tv_downgraded 대신 다른 클라이언트를 사용
        'extractor_args': {
            'youtube': {
                'player_client': ['default', 'web_embedded'],
            }
        },

        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
        'postprocessor_args': {
            'ffmpeg': ['-ar', '16000', '-ac', '1'],
        },
        'quiet': False,
        'no_warnings': True,
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
    target_url = "https://youtu.be/S_M_w-OnUDw?si=Ja6SdyS4RAl3Zfbc"
    download_folder = WATCH_PATH
    file_prefix = "0824_4"

    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        
    download_lossless_audio(target_url, download_folder, file_prefix)