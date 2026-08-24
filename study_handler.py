import time
import os
import json
import shutil
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from extract.pdf_extract import extract_text_from_pdf
from process.llm_gemini import correct_script_with_gemini
from process.llm_gemini import key_summary_with_gemini
from process.notion_sync import trigger_notion_upload

# 운영체제에 따른 선택. 로컬 전사는 기본 Colab 흐름에서 사용하지 않으므로,
# 관련 무거운 패키지는 실제 전사 요청이 있을 때만 불러옵니다.
import platform
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

    def trim_name(self, base_name) : 
        parts = base_name.split('_')
        if len(parts) > 4 : 
            return '_'.join(parts[:4])
        return base_name

    def save_result(self, base_name, text, suffix):
        save_name = f"{base_name}_{suffix}.txt"
        save_path = os.path.join(WATCH_PATH, save_name)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"💾 저장됨: {save_path}")
        # 앞부분 내용 살짝 미리보기
        preview = text[:20] + "..." if len(text) > 20 else text
        print(f"📝 미리보기: {preview}")
        return save_name

    def check_and_start_ai_correction(self, base_name):
        # 짝꿍 파일들의 예상 경로
        audio_txt_path = os.path.join(WATCH_PATH, f"{base_name}_음성스크립트.txt")
        pdf_txt_path = os.path.join(WATCH_PATH, f"{base_name}_강의자료.txt")
        folder_path = os.path.join(WATCH_PATH, f"{base_name}")
        result_json_path = os.path.join(folder_path, f"{base_name}_done.json")
        # 이미 최종본이 있다면 중복 실행 방지
        if os.path.exists(result_json_path) :
            #print(f"이미 '{base_name}'는 분석완료입니다.")
            #print(f"다시 하고 싶으면 '{base_name}' 폴더를 삭제해 주십시오.")
            return False

        # 둘 다 존재한다면? Gemini 출동!
        if os.path.exists(audio_txt_path) and os.path.exists(pdf_txt_path):
            print(f"🔗 [매치 성공] '{base_name}' 자료 쌍을 찾았습니다. AI 교정을 시작합니다.")
            with open(audio_txt_path, 'r', encoding='utf-8') as f:
                audio_text = f.read()
            with open(pdf_txt_path, 'r', encoding='utf-8') as f:
                pdf_text = f.read()

            # 💡 [수정됨] API 호출! (여기서 뻗어도 아래에서 방어합니다)
            # 💡 API 호출!
            corrected_response = correct_script_with_gemini(audio_text, pdf_text)

            # API 응답에서 '텍스트'만 확실하게 꺼내기 (핵심!)
            if not corrected_response or not corrected_response.text or not corrected_response.text.strip():
                print(f"⚠️ '{base_name}' 교정 실패 또는 빈 응답입니다.")
                return False
            corrected_text = corrected_response.text.strip()

            # 요약 작업도 마찬가지로 텍스트만 꺼냅니다.
            summary_response = key_summary_with_gemini(corrected_text, pdf_text)
            if not summary_response or not summary_response.text or not summary_response.text.strip():
                print(f"⚠️ '{base_name}' 요약 실패 또는 빈 응답입니다.")
                return False
            summary_text = summary_response.text.strip()

            # 정상 성공 시에만 파일로 저장 (이제 완벽한 string 형태라 에러가 나지 않습니다)
            self.save_result(base_name, corrected_text, "최종교정본")

            # JSON에도 객체가 아닌 순수 텍스트(string)를 넣어야 에러가 안 납니다!
            analysis_result = {
                "base_name": base_name,
                "corrected_text": corrected_text,
                "summary": summary_text,  # 여기도 summary_text로 변경
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
            return True

        else:
            #print(f"⏳ '{base_name}'의 짝꿍 파일이 아직 없습니다.")
            return False
    def retry_summary_if_failed(self, base_name):
        # 1. 파일들이 이미 이동된 폴더 경로 설정
        folder_path = os.path.join(WATCH_PATH, base_name)
        
        # 2. 폴더 내 필수 파일들 경로
        result_json_path = os.path.join(folder_path, f"{base_name}_done.json")
        corrected_txt_path = os.path.join(folder_path, f"{base_name}_최종교정본.txt")
        pdf_txt_path = os.path.join(folder_path, f"{base_name}_강의자료.txt")

        # 3. 필수 파일 3개가 모두 존재하는지 확인
        if not (os.path.exists(result_json_path) and 
                os.path.exists(corrected_txt_path) and 
                os.path.exists(pdf_txt_path)):
            print(f"⏳ '{base_name}' 요약 재작업에 필요한 파일이 모두 모이지 않았습니다.")
            return

        # 4. JSON 파일 읽어오기
        try:
            with open(result_json_path, 'r', encoding='utf-8') as f:
                analysis_result = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ '{base_name}'의 JSON 파일을 읽는 데 실패했습니다.")
            return

        # 5. Summary가 이미 제대로 있는지 확인
        current_summary = analysis_result.get("summary", "")
        if current_summary and current_summary.strip():
            print(f"✅ '{base_name}'는 이미 요약이 완료되어 있습니다.")
            return

        print(f"🔄 '{base_name}' 요약 누락 감지! 요약 작업을 재시도합니다.")

        # 6. 최종교정본과 강의자료 텍스트 읽기
        with open(corrected_txt_path, 'r', encoding='utf-8') as f:
            corrected_text = f.read()
        with open(pdf_txt_path, 'r', encoding='utf-8') as f:
            pdf_text = f.read()

        # 7. 요약 API 재호출
        summary_response = key_summary_with_gemini(corrected_text, pdf_text)
        summary_text = summary_response.text if summary_response else ""

        if summary_text:
            # 8. 성공했다면 JSON 업데이트 및 덮어쓰기
            analysis_result["summary"] = summary_text
            
            with open(result_json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=4)
            print(f"💾 [업데이트 완료] '{base_name}' 요약본이 정상적으로 추가되었습니다.")
            
            # (선택) 요약본만 텍스트 파일로 따로 남기고 싶다면 주석 해제
            # self.save_result(base_name, summary_text, "요약본")
            # 다만 save_result가 WATCH_PATH에 저장한다면, 폴더 이동 로직이 추가로 필요할 수 있습니다.
        else:
            print(f"⚠️ '{base_name}' 요약 API 재호출 실패. 결과를 받아오지 못했습니다.")