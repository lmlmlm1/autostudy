print("파이썬 스크립트 시작됨")

import time
import os
import sys
import json
import shutil
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from extract.pdf_extract import extract_text_from_pdf
from extract.pdf_image_save import extract_pages_to_images
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import trigger_notion_upload
from process.anki_generator import generate_anki_csv
from study_handler import StudyDataHandler

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

print("import 완료") # main.py 잘 돌아가고 있는지 확인용

# 타겟이 되는 구글 드라이브 내 파일들을 검색, 처리하기 위한 함수
    # 1. 이 함수는 현존하는 파일들 중 처리되지 않은 파일들을 검색하여 처리하는 역할
    # 2. 반면 main.py의 본문에 나오는 WATCHDOG 라이브러리는 새로 들어오는 파일들에 대해 처리하는 역할
def initial_scan(handler):
    """프로그램 시작 시, 아직 처리되지 않은 파일들을 찾아 처리합니다."""
    print("🔍 [초기 스캔] 미처리 파일을 찾는 중...")
    
    # 폴더 내 모든 파일을 리스트업
    all_files = [f for f in os.listdir(WATCH_PATH) if os.path.isfile(os.path.join(WATCH_PATH, f))]
    
    # 리스트에 대해 한개씩 조지기 studyhandler의 on_created()와 똑같게 하면 됨
    # 그런 의미에서 합수를 하나 정의해서 합칠 수도 있을 것 같은데 이건 좀 물어보고 진행함ㅇㅇ
    for file_name in all_files:
        file_path = os.path.join(WATCH_PATH, file_name)
        file_name = os.path.basename(file_path)
        if "_temp" in file_name or file_name.startswith("~$") or file_name.startswith("."):
            continue # return을 사용하면 for 문을 탈출해버리는 불상사; 
        
        # 당장은 trim_name 버그나서 안쓰고 있으니 일단 바꿈!
        # 고쳐진 거 같아서 다시 풀어봄!
        base_name = handler.trim_name(os.path.splitext(file_name)[0])
        # base_name = os.path.splitext(file_name)[0]
        extension = os.path.splitext(file_name)[1].lower()

        # 텍스트 추출이 필요한 원본 파일들 찾기 (이미 텍스트 파일이 존재하면 건너뜁니다)
        text_made = False
        # False 로 출발!

        
        # name_check(my_name)의 오류는 .txt의 name을 가져와서 그걸 바탕으로 이름들을 늘리니까 고장이 났던 것!
        # 다시말해 my_name이 오염되지 않게 주의하는 것이 중요!
        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            if f"{base_name}_음성스크립트.txt" not in all_files:
                print(f"📦 발견: 미처리 음성 파일 -> {file_name}")
                audio_text = extract_text_from_audio(file_path)
                if audio_text:
                    my_name = handler.save_result(base_name, audio_text, "음성스크립트")
                    # 이게 문제가 되던 코드임. save_result는 _음성스크립트를 붙여서 반환함! -> my_name 오염!
                    # 일단 대충 주석 쳐놨으니 의도한 바가 있으면 설명좀

                    # handler.name_check(my_name)
                    handler.name_check(base_name)
                    text_made = True
        
        if extension == '.pdf':
            if f"{base_name}_강의자료.txt" not in all_files:
                print(f"📦 발견: 미처리 PDF 파일 -> {file_name}")
                pdf_text = extract_text_from_pdf(file_path)
                if pdf_text:
                    my_name = handler.save_result(base_name, pdf_text, "강의자료")
                    # handler.name_check(my_name)
                    handler.name_check(base_name)
                    text_made = True
                
                # 스크립트본 있으니까 임시 은퇴
                # print(f"📸 [PDF 팀] 슬라이드 이미지 캡처 중...")
                # extract_pages_to_images(file_path, output_base_dir=WATCH_PATH)

        if text_made : 
            # 교정 및 스크립트 본 만들기
            handler.check_and_start_ai_correction(base_name)
            # 노션 업로드 후 폴더에도 넣기
            trigger_notion_upload(base_name)
            # 신기능! 안키 만들기
            generate_anki_csv(base_name)
        
# main.py 가 직접 실행될 때 처리되는 부분. 내가 몰랐어서 적어놓음
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