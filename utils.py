print("파이썬 스크립트 시작됨")

import time
import os
import json
import shutil
#실시간 감시
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from extract.pdf_extract import extract_text_from_pdf
from extract.audio_extract import extract_text_from_audio
from extract.pdf_image_save import extract_pages_to_images
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import trigger_notion_upload
from study_handler import StudyDataHandler

print("라이브러리 import 완료")

# 🎯 감시할 구글 드라이브 로컬 경로 (현재는 테스트용 폴더)
WATCH_PATH = parent_page_id = os.getenv("WATCH_PATH")


def initial_scan(handler):
    """프로그램 시작 시, 아직 처리되지 않은 파일들을 찾아 처리합니다."""
    print("🔍 [초기 스캔] 미처리 파일을 찾는 중...")

    # 폴더 내 모든 파일 대상으로 하고 싶은 작업이 있다면 여기에서
    # 예시) 미디어 파일만 전부 젼환하고 싶다.
    # all_files = [f for f in os.listdir(WATCH_PATH) if os.path.isfile(os.path.join(WATCH_PATH, f))]
    # for file_name in all_files:
    #     file_path = os.path.join(WATCH_PATH, file_name)
    #     base_name = os.path.splitext(file_name)[0]
    #     extension = os.path.splitext(file_name)[1].lower()
    #     if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
    #         if f"{base_name}_음성스크립트.txt" not in all_files:
    #             print(f"📦 발견: 미처리 음성 파일 -> {file_name}")
    #             audio_text = extract_text_from_audio(file_path)
    #             if audio_text:
    #                 handler.save_result(base_name, audio_text, "음성스크립트")



    # 파일명을 넣고 원하는 작업을 진행. (안하는 작업을 주석처리)
    base_name = "0424_2"

    # file_path = os.path.join(WATCH_PATH, f"{base_name}.mp4")
    # audio_text = extract_text_from_audio(file_path)
    # if audio_text:
    #   handler.save_result(base_name, audio_text, "음성스크립트")

    # file_path = os.path.join(WATCH_PATH, f"{base_name}.pdf")
    # pdf_text = extract_text_from_pdf(file_path)
    # # if pdf_text:
    # #    handler.save_result(base_name, pdf_text, "강의자료")
    # extract_pages_to_images(file_path)
    # # 음성 스크립트와 강의자료.txt가 모두 만들어지고 교정해서 폴더에 넣어버림
    # handler.check_and_start_ai_correction(base_name)

    #이미 _result.json까지 만들어진 것을 노션 업로드만
    target_dir = os.path.join(WATCH_PATH, base_name)
    trigger_notion_upload(base_name, target_dir)
        

if __name__ == "__main__":

    # 🚀 시작하자마자 밀린 숙제(파일)부터 해결!
    event_handler = StudyDataHandler()
    initial_scan(event_handler)    
    print(f"\n✅ 초기 스캔 완료.")