import os
import fitz
from dotenv import load_dotenv
load_dotenv()
WATCH_PATH = os.environ.get("WATCH_PATH")

def merge_scripted_pdfs(watch_path):
    # 1. 병합할 날짜 입력받기
    target_date = input("병합할 날짜를 입력하세요 (예: 0801): ").strip()

    # 2. 해당 날짜로 시작하는 폴더 찾기
    folders = []
    for item in os.listdir(watch_path):
        full_path = os.path.join(watch_path, item)
        # 폴더이면서 '입력날짜_' 로 시작하는 경우만 필터링
        if os.path.isdir(full_path) and item.startswith(f"{target_date}_"):
            folders.append(item)
            
    if not folders:
        print(f"❌ '{watch_path}' 경로에 '{target_date}'(으)로 시작하는 폴더가 없습니다.")
        return

    # 3. 폴더 정렬 (0801_1, 0801_2 순서대로)
    # 뒷자리 숫자를 기준으로 오름차순 정렬
    folders.sort(key=lambda x: int(x.split('_')[1]))
    print(f"📂 총 {len(folders)}개의 폴더를 발견했습니다. 순서대로 병합을 준비합니다.\n")

    merged = fitz.open()
    
    # 4. 각 폴더를 순회하며 PDF 파일 확인 및 병합 리스트 추가
    no_expected_file = False
    for folder in folders:
        folder_path = os.path.join(watch_path, folder)
        expected_pdf = f"{folder}_scripted.pdf"
        pdf_path = os.path.join(folder_path, expected_pdf)
        
        # 파일이 없을 경우 무한 반복 대기
        if not os.path.exists(pdf_path):
            print(f"⚠️ 일시정지: '{folder}' 폴더 내에 '{expected_pdf}' 파일이 없습니다!")
            no_expected_file = True
        else : 
            print(f"✅ 진행중: '{folder}' 폴더 내에 '{expected_pdf}' 파일 확인됨")
            merged.insert_pdf(fitz.open(pdf_path))
    if no_expected_file :
        print("없는 파일이 있으므로 종료합니다.")
        return

    # 5. 최종 병합 및 저장
    output_file = os.path.join(watch_path, "merged", f"{target_date}_merged_scripted.pdf")
    
    print("\n🔄 모든 파일을 병합하는 중입니다...")
    merged.save(output_file)
    merged.close()
    
    print(f"🎉 병합 완료! 결과물이 다음 경로에 저장되었습니다:\n➔ {output_file}")


if __name__ == "__main__":
    merge_scripted_pdfs(WATCH_PATH)