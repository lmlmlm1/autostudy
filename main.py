import time
import os
import sys
import json
import shutil
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 모듈 임포트 (경로명은 실제 구성에 맞게 확인해 주세요)
from extract.pdf_extract import extract_text_from_pdf
from extract.pdf_image_save import extract_pages_to_images
from extract.audio_extract import extract_text_from_audio
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import trigger_notion_upload

# 💡 macOS 백그라운드 실행 시 경로 꼬임 방지를 위한 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 1. 🎯 변수 다중 할당 오류 수정 (분리)
WATCH_PATH = os.getenv("WATCH_PATH")

# 경로 유효성 검사 (시작 전 튕김 방지)
if not WATCH_PATH or not os.path.exists(WATCH_PATH):
    print(f"❌ 오류: 유효한 WATCH_PATH 경로를 찾을 수 없습니다. ({WATCH_PATH})")
    print(".env 파일의 설정을 다시 확인해주세요.")
    sys.exit(1)


# 2. 🛡️ 대용량 파일 씹힘 방지: 스마트 대기 로직
def wait_for_file_to_finish(file_path, wait_time=3):
    """파일 쓰기(다운로드/복사)가 완전히 끝날 때까지 대기합니다."""
    historical_size = -1
    while True:
        try:
            current_size = os.path.getsize(file_path)
        except OSError:
            time.sleep(wait_time)
            continue
        
        # 이전 크기와 현재 크기가 같고, 0바이트가 아니면 복사 완료로 간주
        if current_size == historical_size and current_size > 0:
            return True
            
        historical_size = current_size
        time.sleep(wait_time)


class StudyDataHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        file_name = os.path.basename(file_path)
        extension = os.path.splitext(file_name)[1].lower()
        
        # 임시 파일 무시
        if "_temp" in file_name or file_name.startswith("~$") or file_name.startswith("."):
            return

        print(f"\n[{time.strftime('%H:%M:%S')}] 🚨 새 파일 감지됨, 복사 대기 중...: {file_name}")
        
        # 💡 고정 2초 대기 대신 스마트 대기 실행
        wait_for_file_to_finish(file_path)
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 파일 복사 완료, 처리를 시작합니다: {file_name}")

        base_name = os.path.splitext(file_name)[0]

        # 영상/음성 파일 처리
        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            audio_text = extract_text_from_audio(file_path)
            if audio_text:
                self.save_result(base_name, audio_text, "음성스크립트")
            self.check_and_start_ai_correction(base_name)
            
        # PDF 파일 처리
        elif extension == '.pdf':
            print(f"📄 [PDF 팀] 텍스트 및 슬라이드 이미지 추출 시작: {file_name}")
            
            # 텍스트 추출
            pdf_text = extract_text_from_pdf(file_path)
            if pdf_text:
                self.save_result(base_name, pdf_text, "강의자료")
                
            # 💡 [핵심] 텍스트를 뽑은 직후, 무거운 위스퍼가 돌기 전에 슬라이드 이미지부터 뽑아냅니다.
            print(f"📸 [PDF 팀] 슬라이드 이미지 캡처 중...")
            extract_pages_to_images(file_path, output_base_dir=WATCH_PATH)
            
            self.check_and_start_ai_correction(base_name)
            
        # ❌ [수정 완료] 노션 업로드 트리거가 있던 자리를 깔끔하게 지웠습니다.

    def save_result(self, base_name, text, suffix):
        save_name = f"{base_name}_{suffix}.txt"
        save_path = os.path.join(WATCH_PATH, save_name)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"💾 텍스트 추출 저장됨: {save_path}")

    def check_and_start_ai_correction(self, base_name):
        audio_txt_path = os.path.join(WATCH_PATH, f"{base_name}_음성스크립트.txt")
        pdf_txt_path = os.path.join(WATCH_PATH, f"{base_name}_강의자료.txt")
        
        target_dir = os.path.join(WATCH_PATH, base_name)
        done_json_path = os.path.join(target_dir, f"{base_name}_done.json")
        
        # 이미 최종 처리가 끝난 파일이라면 중복 실행 방지
        if os.path.exists(done_json_path):
            return

        # 둘 다 존재한다면? Gemini 교정 출동!
        if os.path.exists(audio_txt_path) and os.path.exists(pdf_txt_path):
            print(f"🔗 [매치 성공] '{base_name}' 자료 쌍을 찾았습니다. AI 교정을 시작합니다.")
            
            with open(audio_txt_path, 'r', encoding='utf-8') as f:
                audio_text = f.read()
            with open(pdf_txt_path, 'r', encoding='utf-8') as f:
                pdf_text = f.read()

            result = correct_script_with_gemini(audio_text, pdf_text)

            # API 실패 방어 로직
            if result is None or result[0] is None:
                print(f"⚠️ '{base_name}' 교정 실패 (API 오류). 다음 파일 대기 상태로 넘어갑니다.")
                return 

            summary, terms, corrected_text = result

            self.save_result(base_name, corrected_text, "최종교정본")
            
            # 노션 파이프라인으로 넘길 JSON 데이터 생성
            analysis_result = {
                "base_name": base_name,
                "corrected_text": corrected_text,
                "summary": summary,
                "terms": terms,
                "timestamp": time.time()
            }
            
            # 폴더 생성 및 JSON 저장
            os.makedirs(target_dir, exist_ok=True)
            result_json_path = os.path.join(target_dir, f"{base_name}_result.json")
            
            with open(result_json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=4)
            print(f"💾 [저장 완료] '{base_name}' 분석 결과 JSON 생성 완료.")

            # 관련 파일들을 전용 폴더로 모두 이동 (정리)
            for filename in os.listdir(WATCH_PATH):
                file_path = os.path.join(WATCH_PATH, filename)
                if filename.startswith(base_name) and filename != base_name and os.path.isfile(file_path):
                    new_path = os.path.join(target_dir, filename)
                    shutil.move(file_path, new_path)

            # 3. 🎯 [핵심] 폴더 정리가 모두 끝난 이곳에서 노션 업로드를 트리거합니다!
            print(f"🚀 '{base_name}' 노션 업로드를 준비합니다.")
            
            # 💡 [추가 방어] 방금 옮겨진 슬라이드 이미지들이 구글 드라이브 서버에 동기화될 시간을 줍니다.
            print("⏳ 이미지 구글 드라이브 동기화를 위해 잠시 대기합니다 (15초)...")
            time.sleep(15) 
            
            trigger_notion_upload(base_name, target_dir)

            # API RPM 제한 방지
            print("⏳ API RPM 보호를 위해 15초 대기합니다...")
            time.sleep(15)

        else:
            print(f"⏳ '{base_name}'의 짝꿍 파일이 아직 없습니다. 대기합니다.")


def initial_scan(handler):
    """프로그램 시작 시, 밀린 파일을 찾아 처리합니다."""
    print("🔍 [초기 스캔] 미처리 파일을 찾는 중...")
    all_files = [f for f in os.listdir(WATCH_PATH) if os.path.isfile(os.path.join(WATCH_PATH, f))]
    
    # 먼저 텍스트 파일들을 추출해 둡니다.
    for file_name in all_files:
        if file_name.startswith("~$") or file_name.startswith("."): continue
        
        file_path = os.path.join(WATCH_PATH, file_name)
        base_name = os.path.splitext(file_name)[0]
        extension = os.path.splitext(file_name)[1].lower()

        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            if f"{base_name}_음성스크립트.txt" not in all_files:
                audio_text = extract_text_from_audio(file_path)
                if audio_text: handler.save_result(base_name, audio_text, "음성스크립트")
        
        elif extension == '.pdf':
            if f"{base_name}_강의자료.txt" not in all_files:
                pdf_text = extract_text_from_pdf(file_path)
                if pdf_text: handler.save_result(base_name, pdf_text, "강의자료")
                
                # 밀린 PDF를 처리할 때도 이미지 캡처를 진행합니다.
                extract_pages_to_images(file_path, output_base_dir=WATCH_PATH)

    # 추출이 끝난 후 짝꿍이 맞춰진 파일들을 AI 교정으로 넘깁니다.
    processed_bases = set()
    for file_name in os.listdir(WATCH_PATH):
        if file_name.endswith("_음성스크립트.txt") or file_name.endswith("_강의자료.txt"):
            base_name = file_name.replace("_음성스크립트.txt", "").replace("_강의자료.txt", "")
            if base_name not in processed_bases:
                handler.check_and_start_ai_correction(base_name)
                processed_bases.add(base_name)


if __name__ == "__main__":
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
        print("\n🛑 사용자에 의해 폴더 감시를 종료합니다.")
        observer.stop()
    observer.join()