import time
import os
import json
import shutil
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from extract.pdf_extract import extract_text_from_pdf
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import trigger_notion_upload

#운영체제에 따른 선택
import platform
# 현재 운영체제 확인
if platform.system() == 'Darwin':  # Mac인 경우
    from extract.audio_extract_mac import extract_text_from_audio    
    # 💡 macOS 백그라운드 실행 시 경로 꼬임 방지를 위한 절대 경로 설정
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(BASE_DIR, '.env'))
else:  # Windows나 Linux인 경우
    from extract.audio_extract_windows import extract_text_from_audio
# 🎯 감시할 구글 드라이브 로컬 경로 (현재는 테스트용 폴더)
WATCH_PATH = os.getenv("WATCH_PATH")

class StudyDataHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        file_name = os.path.basename(file_path)
        extension = os.path.splitext(file_name)[1].lower()
        
        # 파일이 완전히 복사될 때까지 아주 잠시 대기 (용량이 큰 영상 파일 씹힘 방지)
        time.sleep(2)
        
        print(f"\n[{time.strftime('%H:%M:%S')}] 🚨 새 파일 감지됨: {file_name}")
        if "_temp" in file_name or file_name.startswith("~$"):
            print("임시파일이므로 무시합니다.")
            return

        base_name = os.path.splitext(file_name)[0]
        # 영상/음성 파일인 경우 텍스트 추출 파이프라인 시작
        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            audio_text = extract_text_from_audio(file_path)
            self.save_result(base_name, audio_text, "음성스크립트")
        # pdf라면 
        if extension == '.pdf':
            pdf_text = extract_text_from_pdf(file_path)
            self.save_result(base_name, pdf_text, "강의자료")
        
        if extension in ['.mp4', '.m4a', '.mp3', '.wav', '.pdf']:
            self.check_and_start_ai_correction(base_name)
            target_dir = os.path.join(WATCH_PATH, base_name)
            trigger_notion_upload(base_name, target_dir)

    def save_result(self, base_name, text, suffix):
        save_name = f"{base_name}_{suffix}.txt"
        save_path = os.path.join(WATCH_PATH, save_name)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"💾 저장됨: {save_path}")
        # 앞부분 내용 살짝 미리보기
        preview = text[:20] + "..." if len(text) > 20 else text
        print(f"📝 미리보기: {preview}")

    def check_and_start_ai_correction(self, base_name):
        # 짝꿍 파일들의 예상 경로
        audio_txt_path = os.path.join(WATCH_PATH, f"{base_name}_음성스크립트.txt")
        pdf_txt_path = os.path.join(WATCH_PATH, f"{base_name}_강의자료.txt")
        folder_path = os.path.join(WATCH_PATH, f"{base_name}")
        result_json_path = os.path.join(folder_path, f"{base_name}_done.json")
        # 이미 최종본이 있다면 중복 실행 방지
        if os.path.exists(result_json_path) :
            print(f"이미 '{base_name}'는 분석완료입니다.")
            print(f"다시 하고 싶으면 '{base_name}' 폴더를 삭제해 주십시오.")
            return

        # 둘 다 존재한다면? Gemini 출동!
        if os.path.exists(audio_txt_path) and os.path.exists(pdf_txt_path):
            print(f"🔗 [매치 성공] '{base_name}' 자료 쌍을 찾았습니다. AI 교정을 시작합니다.")
            with open(audio_txt_path, 'r', encoding='utf-8') as f:
                audio_text = f.read()
            with open(pdf_txt_path, 'r', encoding='utf-8') as f:
                pdf_text = f.read()

            # 💡 [수정됨] API 호출! (여기서 뻗어도 아래에서 방어합니다)
            result = correct_script_with_gemini(audio_text, pdf_text)
            # 🛡️ [수정됨] 에러 방패: API가 실패해서 None을 반환했다면 여기서 스톱! (에러 튕김 방지)
            if result is None or result[0] is None:
                print(f"⚠️ '{base_name}' 교정 실패 (API 오류). 프로그램 종료 없이 다음 파일 대기 상태로 넘어갑니다.")
                return 
            # 정상 성공 시에만 변수에 담기
            summary, terms, corrected_text = result
            self.save_result(base_name, corrected_text, "최종교정본")


            analysis_result = {
                "base_name": base_name,
                "corrected_text": corrected_text,
                "summary": summary,
                "terms": terms,
                "timestamp": time.time()
            }
            result_json_path = os.path.join(WATCH_PATH, f"{base_name}_result.json")
            with open(result_json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=4)
            print(f"💾 [저장 완료] '{base_name}' 분석 결과가 저장되었습니다.")

            # 전용 폴더 생성
            target_dir = os.path.join(WATCH_PATH, base_name)
            os.makedirs(target_dir, exist_ok=True)
            # 관련 모든 파일 이동 (mp4, pdf, txt 등)
            # WATCH_PATH에 있는 base_name으로 시작하는 모든 파일을 새 폴더로 옮깁니다.
            for filename in os.listdir(WATCH_PATH):
                if filename.startswith(base_name) and filename != base_name: # 폴더 자신 제외
                    old_path = os.path.join(WATCH_PATH, filename)
                    new_path = os.path.join(target_dir, filename)
                    time.sleep(1)
                    shutil.move(old_path, new_path)

        else:
            print(f"⏳ '{base_name}'의 짝꿍 파일이 아직 없습니다.")