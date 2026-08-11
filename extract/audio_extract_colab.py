"""
이 파일은 Windows나 WSL2가 아니라 Colab VM 안에서 실행됩니다.
위치: My Drive/2026-1/scripts/audio_extract_colab.py
Colab에서의 실제 경로: /content/drive/MyDrive/2026-1/scripts/audio_extract_colab.py
"""

import os
import argparse
from faster_whisper import WhisperModel
from moviepy import VideoFileClip
from google import genai
from pydub import AudioSegment, silence

print("🧠 [Audio 팀] Faster-Whisper AI 준비 중 (NVIDIA GPU / Colab)...")

_model = None
_client = None


def get_model(model_size="large-v3", device="cuda", compute_type="float16"):
    global _model
    if _model is None:
        print(f"📥 Whisper 모델 로딩 중: {model_size} ({device}, {compute_type})")
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model


def get_client(api_key):
    global _client
    if _client is None:
        _client = genai.Client(api_key=api_key)
    return _client


def get_dynamic_prompt(audio_file_path, api_key):
    base_path = os.path.splitext(audio_file_path)[0]
    txt_path = f"{base_path}_강의자료.txt"
    if not os.path.exists(txt_path):
        return None

    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        query = f"다음 의학 강의록에서 핵심 전문 용어 20개만 쉼표로 연결해 추출하세요:\n{content}"
        client = get_client(api_key)
        response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=query)
        keywords = response.text.strip()

        final_prompt = f"의학 강의 키워드: {keywords}."
        return final_prompt[:200]

    except Exception as e:
        print(f"⚠️ 프롬프트 생성 실패: {e}")
        return None


def extract_and_compress_audio(video_path):
    base_path = os.path.splitext(video_path)[0]
    temp_audio_path = f"{base_path}_temp.wav"
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(
        temp_audio_path, fps=16000, nbytes=2, codec='pcm_s16le',
        ffmpeg_params=["-ac", "1"], logger=None
    )
    video.close()
    return temp_audio_path


def apply_vad_preprocessing(audio_path):
    print("✂️ [VAD] 오디오 분석 및 침묵 제거 시작...")
    audio = AudioSegment.from_file(audio_path)
    orig_duration = len(audio) / 1000.0

    adaptive_thresh = audio.dBFS - 16
    print(f"📊 오디오 평균 볼륨: {audio.dBFS:.2f}dB | 설정된 임계값: {adaptive_thresh:.2f}dB")

    chunks = silence.split_on_silence(
        audio,
        min_silence_len=2000,
        silence_thresh=adaptive_thresh,
        keep_silence=500
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


def extract_text_from_audio(file_path, api_key, model_size="large-v3"):
    print(f"\n🎙️ 스크립트 추출 시작: {os.path.basename(file_path)}")
    extension = os.path.splitext(file_path)[1].lower()
    temp_files = []

    if extension == '.mp4':
        target_path = extract_and_compress_audio(file_path)
        temp_files.append(target_path)
    else:
        target_path = file_path

    cleaned_path = apply_vad_preprocessing(target_path)
    if cleaned_path != target_path:
        temp_files.append(cleaned_path)

    dynamic_initial_prompt = get_dynamic_prompt(file_path, api_key)

    try:
        model = get_model(model_size=model_size)

        segments, info = model.transcribe(
            cleaned_path,
            language="ko",
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.0,
            log_prob_threshold=-1.0,
            temperature=(0.0, 0.1, 0.2, 0.4, 0.6, 0.8),
            initial_prompt=dynamic_initial_prompt,
            vad_filter=False,
        )

        script_text = "".join(segment.text for segment in segments).strip()

        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

        return script_text

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
        return None


def main():
    parser = argparse.ArgumentParser(description="Colab GPU 기반 강의 오디오 전사")
    parser.add_argument("--input", required=True, help="Colab 기준 입력 파일 경로 (/content/drive/MyDrive/...)")
    parser.add_argument("--output", required=True, help="Colab 기준 결과 저장 경로 (/content/drive/MyDrive/...)")
    parser.add_argument("--model-size", default="large-v3")
    parser.add_argument("--api-key", required=True, help="Gemini API 키")
    args = parser.parse_args()

    result = extract_text_from_audio(args.input, args.api_key, model_size=args.model_size)

    if result is None:
        raise SystemExit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"✅ 완료: {args.output}")


if __name__ == "__main__":
    main()