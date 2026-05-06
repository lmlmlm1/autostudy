import time
import os
import json
import shutil
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from extract.pdf_extract import extract_text_from_pdf
from extract.pdf_image_save import extract_pages_to_images
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import trigger_notion_upload
from process.pdf_script_come_together import append_scripts_to_pdf

# 운영체제에 따른 선택
import platform
# 현재 운영체제 확인
if platform.system() == 'Darwin':  # Mac인 경우
    from extract.audio_extract_mac import extract_text_from_audio    
else:  # Windows나 Linux인 경우
    from extract.audio_extract_windows import extract_text_from_audio

# OS 종류 상관없이 백그라운드 실행 시 경로 꼬임 방지를 위한 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
# 감시할 구글 드라이브 로컬 경로
WATCH_PATH = os.getenv("WATCH_PATH")

class StudyDataHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:  # 새로 만들어진 것이 폴더면 무시
            return
        
        file_path = event.src_path                          # 현재 event 가 발생한 곳의 전체주소를 불러오기
        file_name = os.path.basename(file_path)             # 전체 주소 중 마지막 부분, 즉 file_name을 불러오기
        extension = os.path.splitext(file_name)[1].lower()  # file_name 중 . 다음에 존재하는 "확장자" 를 불러오기
        
        time.sleep(2)   # 파일이 완전히 복사될 때까지 아주 잠시 대기 (용량이 큰 영상 파일 씹힘 방지)
        
        print(f"\n[{time.strftime('%H:%M:%S')}] 🚨 새 파일 감지됨: {file_name}") # 새로운 파일의 이름, 추가된 시간을 출력
        if "_temp" in file_name or file_name.startswith("~$"):      # temp 파일이면 무시하고
            print("임시파일이므로 무시합니다.")
            return

        base_name = os.path.splitext(file_name)[0]                  # 확장자를 뗀 부분을 base_name 으로 받아옴 
        
        # 영상/음성 파일인 경우 텍스트 추출 파이프라인 시작
        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            audio_text = extract_text_from_audio(file_path)
            self.save_result(base_name, audio_text, "음성스크립트")

        # pdf라면
        if extension == '.pdf':
            print(f"📦 발견: 미처리 PDF 파일 -> {file_name} 새로운 파일이므로 작업을 순차적으로 진행합니다.")
            print(f"📦 발견: 새로운 파일이므로 작업을 순차적으로 진행합니다.")
            pdf_text = extract_text_from_pdf(file_path)         # 1. 텍스트를 추출 후 저장 (OCR 포함)
            self.save_result(base_name, pdf_text, "강의자료")

            # print(f"📸 [PDF 팀] 슬라이드 이미지 캡처 중...")        # 2. 슬라이드 이미지를 캡처하여 구글드라이브 업로드
            # extract_pages_to_images(file_path, output_base_dir=WATCH_PATH)
            # 근데 어차피 스트립트본 만드니까 필요없을지도?

        if extension in ['.mp4', '.m4a', '.mp3', '.wav', '.pdf']:
            # 두 파일이 다 존재하는 지 확인 후 교정 시작 (및 스크립트본 생성)
            self.check_and_start_ai_correction(base_name)
            #노션 업로드 및 파일 이름 done 으로 바꾸기
            target_dir = os.path.join(WATCH_PATH, base_name)
            trigger_notion_upload(base_name, target_dir)

        # 추가된 파일이  pdf 면 2번째, 3번째 if 를 돌고
        #            영상이면 1번째, 3번째 if 를 돈다.
        # 두 개 다 추가되면 2 -> 3 실패 / 1 -> 3 성공 해서 1, 2, 3 다 돎

    # 다음 두 함수는 뭐 해보려다가 실패한 듯?
    # 고장난 이유를 짐작해보면 이름 늘리는 로직을 짯더니 '_음성스크립트'에 다 잡아멱혀 버림 ㅠㅠ
    def name_check(self, my_name) :
        my_base = os.path.splitext(my_name)[0]
        your_base = my_base
        for file_name in os.listdir(WATCH_PATH):
            file_path = os.path.join(WATCH_PATH, file_name)
            file_base = os.path.splitext(file_name)[0]
            file_extension = os.path.splitext(file_name)[1]
            if file_base in my_base :
                new_path = os.path.join(WATCH_PATH, my_base + file_extension)
                os.rename(file_path, new_path)
            if your_base in file_name : 
                your_base = file_base
        if my_base != your_base : 
            my_path = os.path.join(WATCH_PATH, my_name)
            your_path = os.path.join(WATCH_PATH, your_base + os.path.splitext(my_name)[1])
            os.rename(my_path, your_path)

    def trim_name(self, base_name) : 
        parts = base_name.split('_')
        if len(parts) > 4 : 
            return '_'.join(parts[:4])
        return base_name

    # 저장할 base_name, 파일 종류?(음성스크립트, 교정본 등등...), 저장할 텍스트를 주면 알잘딱
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
        # 이미 최종본(done)이 있다면 중복 실행 방지
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

            # 여기서 저장하기 직전에 [슬라이드 01] 같은 거추장스러운 부분들 없애버리는 것도 방법일듯..?
            # 어차피 스크립트본 따로 만들건데 뭐
            self.save_result(base_name, corrected_text, "최종교정본")

            # _result.json 으로 교정 결과 저장하기
            analysis_result = {
                "base_name": base_name,
                "corrected_text": corrected_text,
                "summary": summary,
                "terms": terms,
                "timestamp": time.time()
            }

            # 열고 내용 떄려박기
            result_json_path = os.path.join(WATCH_PATH, f"{base_name}_result.json")
            with open(result_json_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=4)
            print(f"💾 [저장 완료] '{base_name}' 분석 결과가 저장되었습니다.")

            # 스크립트본도 겸사겸사 만들어버리고 폴더에 쑤셔박어
            append_scripts_to_pdf(base_name)

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