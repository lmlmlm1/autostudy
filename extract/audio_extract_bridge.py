"""
Windows에서 실행되는 파일입니다.
기존 audio_extract_mac.py 의 extract_text_from_audio(file_path) 와
동일한 시그니처를 가지므로, 호출하는 쪽 코드는 아래처럼 import 문만 바꾸면 됩니다.

    # 기존
    from audio_extract_mac import extract_text_from_audio

    # 변경
    from audio_extract_bridge import extract_text_from_audio

    audio_text = extract_text_from_audio(file_path)   # 호출부는 그대로

실제로 google colab 환경에서는 audio_extract_colab가 굴러갈 겂입니다.
"""

import os
import time
import subprocess

# ---- 환경에 맞게 아래 3개만 수정하세요 -----------------------------
GEMINI_API_KEY = os.getenv("API_KEY")  # Windows 쪽 환경변수에서 그대로 읽음
COLAB_SCRIPT_DRIVE_PATH = "My Drive/2026-1/scripts/audio_extract_colab.py"
GPU_TYPE = "T4"
# --------------------------------------------------------------------

SYNC_WAIT_TIMEOUT = 120   # Drive 동기화 대기 최대 초
SYNC_WAIT_INTERVAL = 2    # 폴링 간격 초


def to_wsl_path(win_path: str) -> str:
    result = subprocess.run(
        ["wsl", "wslpath", "-a", win_path],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def wsl_to_colab_drive_path(wsl_path: str) -> str:
    # /mnt/g/My Drive/2026-1/file.m4a -> /content/drive/MyDrive/2026-1/file.m4a
    marker = "My Drive/"
    idx = wsl_path.find(marker)
    if idx == -1:
        raise ValueError(f"Google Drive 경로가 아닌 것 같습니다: {wsl_path}")
    relative = wsl_path[idx + len(marker):]
    return f"/content/drive/MyDrive/{relative}"


def wait_for_local_file(path: str, timeout: int = SYNC_WAIT_TIMEOUT) -> bool:
    """Colab이 Drive에 쓴 파일이 로컬 Drive 동기화 클라이언트를 통해
    Windows 쪽에 나타날 때까지 대기합니다."""
    waited = 0
    while waited < timeout:
        if os.path.exists(path):
            # 동기화 도중 파일이 잡히는 것을 방지하기 위해 크기가 안정될 때까지 한 번 더 확인
            size1 = os.path.getsize(path)
            time.sleep(1)
            if os.path.exists(path) and os.path.getsize(path) == size1:
                return True
        time.sleep(SYNC_WAIT_INTERVAL)
        waited += SYNC_WAIT_INTERVAL
    return False


def extract_text_from_audio(file_path: str, model_size: str = "large-v3") -> str | None:
    """기존 mac 버전과 동일한 시그니처. 내부적으로 WSL2 -> Colab GPU로 처리."""

    if not GEMINI_API_KEY:
        print("⚠️ API_KEY 환경변수가 설정되어 있지 않습니다.")

    base_path = os.path.splitext(file_path)[0]
    output_win_path = f"{base_path}_transcript_temp.txt"

    wsl_input = to_wsl_path(file_path)
    wsl_output = to_wsl_path(output_win_path)
    wsl_script = to_wsl_path(r"G:\내 드라이브\\" + COLAB_SCRIPT_DRIVE_PATH.replace("My Drive/", ""))

    colab_input = wsl_to_colab_drive_path(wsl_input)
    colab_output = wsl_to_colab_drive_path(wsl_output)
    colab_script = f"/content/drive/MyDrive/{COLAB_SCRIPT_DRIVE_PATH.split('My Drive/')[-1]}"

    cmd = [
        "wsl", "bash", "-lc",
        f"colab new --gpu {GPU_TYPE} && "
        f"colab exec \"pip install -q faster-whisper moviepy pydub google-genai\" && "
        f"colab run '{colab_script}' "
        f"--input '{colab_input}' --output '{colab_output}' "
        f"--model-size {model_size} --api-key '{GEMINI_API_KEY}' && "
        f"colab stop"
    ]

    print(f"🚀 Colab GPU로 전사 요청 중: {os.path.basename(file_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Colab 작업 실패:\n{result.stderr}")
        return None

    print("⏳ Drive 동기화 대기 중...")
    if not wait_for_local_file(output_win_path):
        print(f"❌ 결과 파일이 시간 내에 동기화되지 않았습니다: {output_win_path}")
        return None

    with open(output_win_path, "r", encoding="utf-8") as f:
        text = f.read()

    os.remove(output_win_path)
    return text