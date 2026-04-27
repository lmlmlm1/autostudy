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
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import trigger_notion_upload
from study_handler import StudyDataHandler

print("라이브러리 import 완료")

# 🎯 감시할 구글 드라이브 로컬 경로 (현재는 테스트용 폴더)
WATCH_PATH = parent_page_id = os.getenv("WATCH_PATH")


def initial_scan(handler):
    """프로그램 시작 시, 아직 처리되지 않은 파일들을 찾아 처리합니다."""
    print("🔍 [초기 스캔] 미처리 파일을 찾는 중...")
    
    # 폴더 내 모든 파일을 리스트업
    all_files = [f for f in os.listdir(WATCH_PATH) if os.path.isfile(os.path.join(WATCH_PATH, f))]
    
    for file_name in all_files:
        file_path = os.path.join(WATCH_PATH, file_name)
        base_name = os.path.splitext(file_name)[0]
        extension = os.path.splitext(file_name)[1].lower()

        # 텍스트 추출이 필요한 원본 파일들 찾기
        # (이미 텍스트 파일이 존재하면 건너뜁니다)
        
        text_made = False
        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            if f"{base_name}_음성스크립트.txt" not in all_files:
                print(f"📦 발견: 미처리 음성 파일 -> {file_name}")
                audio_text = extract_text_from_audio(file_path)
                if audio_text:
                    handler.save_result(base_name, audio_text, "음성스크립트")
                    text_made = True
        
        if extension == '.pdf':
            if f"{base_name}_강의자료.txt" not in all_files:
                print(f"📦 발견: 미처리 PDF 파일 -> {file_name}")
                pdf_text = extract_text_from_pdf(file_path)
                if pdf_text:
                    handler.save_result(base_name, pdf_text, "강의자료")
                    text_made = True

        if text_made : 
            handler.check_and_start_ai_correction(base_name)
            target_dir = os.path.join(WATCH_PATH, base_name)
            trigger_notion_upload(base_name, target_dir)
        

if __name__ == "__main__":

    # 🚀 시작하자마자 밀린 숙제(파일)부터 해결!
    event_handler = StudyDataHandler()
    initial_scan(event_handler)    
    print(f"\n✅ 초기 스캔 완료.")
    print(f"👀 폴더 감시를 시작합니다: {WATCH_PATH}")
    print("종료하려면 Ctrl+C를 누르세요.\n" + "="*40)
    
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=False)
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n감시를 종료합니다.")
        observer.stop()
    observer.join()