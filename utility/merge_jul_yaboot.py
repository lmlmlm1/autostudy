import fitz  # PyMuPDF
from difflib import SequenceMatcher
import imagehash
from PIL import Image
import io
from pathlib import Path
import unicodedata
import re
import os
import shutil
from dotenv import load_dotenv
load_dotenv()
WATCH_PATH = os.environ.get("WATCH_PATH")

# ─────────────────────────────────────────────────────────────
# 필기 앱이 타이핑 텍스트를 실제 텍스트 객체로 넣는 경우에만 의미가 있음.
# 본인 갤럭시탭 필기 PDF에서 발견한 낯선 폰트명이 있으면 여기에 추가하세요.
# (진단 스크립트로 확인 후 채워 넣을 것 — 채팅에서 안내한 스크립트 참고)
IGNORE_FONTS_DEFAULT = ["Handwriting", "Pen", "AppleSDGothicNeo"]
# ─────────────────────────────────────────────────────────────


def get_clean_text(page, ignore_fonts=None):
    if ignore_fonts is None:
        ignore_fonts = IGNORE_FONTS_DEFAULT
    text_dict = page.get_text("dict")
    clean_text = ""
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_name = span.get("font", "").lower()
                    if not any(ignore_font.lower() in font_name for ignore_font in ignore_fonts):
                        clean_text += span.get("text", "") + " "
    return clean_text.strip()


def get_similarity(text1, text2):
    if not text1 and not text2:
        return 1.0
    return SequenceMatcher(None, text1, text2).ratio()


def image_hash_diff(page_a, page_b):
    """두 페이지를 흑백 저해상도로 렌더링해 지각적 해시 차이를 반환. 값이 작을수록 시각적으로 유사."""
    mat = fitz.Matrix(0.5, 0.5)
    img_a = Image.open(io.BytesIO(page_a.get_pixmap(matrix=mat, colorspace=fitz.csGRAY).tobytes("png")))
    img_b = Image.open(io.BytesIO(page_b.get_pixmap(matrix=mat, colorspace=fitz.csGRAY).tobytes("png")))
    hash_a = imagehash.average_hash(img_a, hash_size=8)
    hash_b = imagehash.average_hash(img_b, hash_size=8)
    return hash_a - hash_b


def fallback_hash_compare(page_jul, page_yaboot):
    return image_hash_diff(page_jul, page_yaboot)


def page1_has_annotation(jul_pdf, yaboot_pdf, hash_threshold=12):
    """
    폰트명 대신 시각적 차이로 1페이지 필기 유무 판단.
    줄필기 1p가 야붙 1p와 눈에 띄게 다르면(하이라이트/필기 등) True.
    기기(아이패드/갤럭시탭)와 무관하게 동작.
    """
    diff = image_hash_diff(jul_pdf[0], yaboot_pdf[0])
    return diff > hash_threshold

def name_trim(file_path):
    # 지정한 폴더 내의 모든 파일 목록 가져오기
    try:
        files = os.listdir(file_path)
    except FileNotFoundError:
        print(f"❌ '{file_path}' 경로를 찾을 수 없습니다.")
        return

    print(f"📂 '{file_path}' 폴더의 파일 이름 변경을 시작합니다...\n")

    for filename in files:
        full_path = os.path.join(file_path, filename)
        
        # 폴더는 건너뛰고 '파일'이면서 '.pdf'인 경우만 처리
        if os.path.isfile(full_path) and filename.lower().endswith(".pdf"):
            
            # 파일 이름의 앞 6글자 추출 
            # (이름이 6글자보다 짧아도 에러 없이 있는 만큼만 가져옵니다)
            first_6_chars = filename[:6]
            
            # 조건에 따른 새 파일 이름 결정
            # 만일 야붙에 필기한 경우, 굳이 merge할 필요가 없음
            if filename.endswith("야붙필기.pdf") or filename.endswith("야붙.pdf.pdf"): 
                new_full_path = file_path.parent / f"{first_6_chars}.pdf"
            elif filename.endswith("야붙.pdf") or filename.endswith("yaboot.pdf"):
                new_full_path = file_path / f"{first_6_chars}_yaboot.pdf"
            else:
                new_full_path = file_path / f"{first_6_chars}_jul.pdf"
            
            # 이름 변경 실행 (이미 같은 이름이 존재하면 에러가 날 수 있으므로 예외 처리)
            try:
                shutil.copy2(full_path, new_full_path)
                print(f"✅ 복사 완료: 원본 유지됨 ➔ '{new_full_path.name}' 생성")
                #os.rename(full_path, new_full_path)
                #print(f"🔄 변경 완료: '{filename}' ➔ '{new_full_path.name}'")
            except FileExistsError:
                print(f"⚠️ 덮어쓰기 오류: '{new_full_path.name}' 파일이 이미 존재하여 '{filename}'을 변경할 수 없습니다.")
            except Exception as e:
                print(f"❌ '{new_full_path.name}' 변경 중 오류 발생: {e}")


def merge_lecture_notes(jul_path, yaboot_path, output_main, output_verify,
                         sim_threshold=0.8, hash_threshold=12, lookahead=5):
    jul_pdf = fitz.open(jul_path)
    yaboot_pdf = fitz.open(yaboot_path)
    out_pdf = fitz.open()
    verify_pdf = fitz.open()

    rect_top = fitz.Rect(0, 0, 595, 421)
    rect_bottom = fitz.Rect(0, 421, 595, 842)

    def add_verify_page(jul_idx=None, yaboot_idx=None):
        page = verify_pdf.new_page(width=595, height=842)
        if jul_idx is not None:
            page.show_pdf_page(rect_top, jul_pdf, jul_idx)
        if yaboot_idx is not None:
            page.show_pdf_page(rect_bottom, yaboot_pdf, yaboot_idx)

    i, j = 0, 0
    total_jul = len(jul_pdf)
    total_yaboot = len(yaboot_pdf)

    clean_output_name = unicodedata.normalize('NFC', Path(output_main).name)
    print(f"\n[{clean_output_name}] 문서 병합을 시작합니다...")

    if total_jul > 0 and total_yaboot > 0:
        print("  [1p 특수규칙] 야붙 1p 줄필기 1p 무조건 삽입")
        out_pdf.insert_pdf(yaboot_pdf, from_page=0, to_page=0)
        add_verify_page(yaboot_idx=0)
        out_pdf.insert_pdf(jul_pdf, from_page=0, to_page=0)
        add_verify_page(jul_idx=0)

        i += 1
        j += 1

    while i < total_jul and j < total_yaboot:
        text_jul = get_clean_text(jul_pdf[i])
        text_yaboot = get_clean_text(yaboot_pdf[j])

        sim = get_similarity(text_jul, text_yaboot)

        if sim >= sim_threshold:
            #print(f"  [일치] 줄필기 {i+1}p == 야붙 {j+1}p (텍스트 유사도: {sim:.2f})")
            out_pdf.insert_pdf(jul_pdf, from_page=i, to_page=i)
            add_verify_page(jul_idx=i, yaboot_idx=j)
            i += 1
            j += 1
            continue

        match_found = False

        for offset in range(1, lookahead + 1):
            if j + offset < total_yaboot:
                future_yaboot_text = get_clean_text(yaboot_pdf[j + offset])
                if get_similarity(text_jul, future_yaboot_text) >= sim_threshold:
                    print(f"  [추가] 야붙 {j+1}p ~ {j+offset}p 삽입 (기출문제)")
                    out_pdf.insert_pdf(yaboot_pdf, from_page=j, to_page=j + offset - 1)
                    for k in range(j, j + offset):
                        add_verify_page(yaboot_idx=k)
                    j += offset
                    match_found = True
                    break

            if i + offset < total_jul:
                future_jul_text = get_clean_text(jul_pdf[i + offset])
                if get_similarity(future_jul_text, text_yaboot) >= sim_threshold:
                    print(f"  [유지] 줄필기 {i+1}p ~ {i+offset}p 삽입 (줄필기에만 있는 내용)")
                    out_pdf.insert_pdf(jul_pdf, from_page=i, to_page=i + offset - 1)
                    for k in range(i, i + offset):
                        add_verify_page(jul_idx=k)
                    i += offset
                    match_found = True
                    break

        if not match_found:
            print(f"  [경고] 텍스트 매칭 실패! (줄필기 {i+1}p, 야붙 {j+1}p). 📸 해시 비교 가동...")
            hash_diff = fallback_hash_compare(jul_pdf[i], yaboot_pdf[j])

            if hash_diff <= hash_threshold:
                print(f"    👉 [구사일생] 사진 실루엣이 동일함! (차이: {hash_diff}) -> 한 페이지만 삽입")
                out_pdf.insert_pdf(jul_pdf, from_page=i, to_page=i)
                add_verify_page(jul_idx=i, yaboot_idx=j)
                i += 1
                j += 1
            else:
                print(f"    👉 [완전 다름] 해시 비교도 실패. 모두 삽입 (차이: {hash_diff})")
                out_pdf.insert_pdf(jul_pdf, from_page=i, to_page=i)
                add_verify_page(jul_idx=i)
                out_pdf.insert_pdf(yaboot_pdf, from_page=j, to_page=j)
                add_verify_page(yaboot_idx=j)
                i += 1
                j += 1

    if i < total_jul:
        out_pdf.insert_pdf(jul_pdf, from_page=i, to_page=total_jul - 1)
        for k in range(i, total_jul):
            add_verify_page(jul_idx=k)
    if j < total_yaboot:
        out_pdf.insert_pdf(yaboot_pdf, from_page=j, to_page=total_yaboot - 1)
        for k in range(j, total_yaboot):
            add_verify_page(yaboot_idx=k)

    out_pdf.save(output_main, garbage=4, deflate=True)
    out_pdf.close()

    #verify_pdf.save(output_verify, garbage=4, deflate=True)
    verify_pdf.close()

    jul_pdf.close()
    yaboot_pdf.close()

    os.remove(jul_path)
    os.remove(yaboot_path)
    print(f"✅ 완료! 메인/검수 파일 처리가 성공적으로 끝났습니다.")


def process_all_files_in_directory(directory_path, output_dir_path, interactive=True):
    target_dir = Path(directory_path)
    output_dir = Path(output_dir_path)

    if not target_dir.exists() or not target_dir.is_dir():
        print(f"[오류] 원본 파일이 있는 '{directory_path}' 폴더를 찾을 수 없습니다.")
        return

    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    name_trim(target_dir)

    print(f"📂 '{target_dir.resolve()}' 폴더 스캔을 시작합니다...\n" + "="*50)

    all_pdfs = list(target_dir.glob("*.pdf"))
    files_dict = {}

    pattern = re.compile(r"^(\d{4})_([0-9\s,교시]+)(?:_|$)")

    for pdf in all_pdfs:
        clean_stem = unicodedata.normalize('NFC', pdf.stem)
        match = pattern.search(clean_stem)

        if match:
            date_part = match.group(1)
            raw_class_part = match.group(2)

            clean_class_part = re.sub(r'[^\d]', '', raw_class_part)
            unified_key = f"{date_part}_{clean_class_part}"

            if unified_key not in files_dict:
                files_dict[unified_key] = {}

            # 접미사를 _jul / _yaboot 기준으로 판별
            if clean_stem.endswith("_jul"):
                files_dict[unified_key]['jul'] = pdf
                files_dict[unified_key]['display_name'] = clean_stem[:-len("_jul")]
            elif clean_stem.endswith("_yaboot"):
                files_dict[unified_key]['yaboot'] = pdf
                if 'display_name' not in files_dict[unified_key]:
                    files_dict[unified_key]['display_name'] = clean_stem[:-len("_yaboot")]

    processed_count = 0
    for unified_key, pairs in files_dict.items():
        if 'jul' in pairs and 'yaboot' in pairs:

            display_name = pairs.get('display_name', unified_key)
            output_main_path = output_dir / f"{unified_key}.pdf"

            # 이미 병합된 결과물이 있으면 건너뜀 (재실행 시 중복 작업 방지)
            if output_main_path.exists():
                print(f"⏭️  '{unified_key}.pdf' 이미 존재 -> 건너뜀")
                continue

            if interactive:
                user_input = input(f"[작업 가능: {display_name}.pdf] 진행하시겠습니까? (엔터: 종료, 아무키+엔터: 진행) ")
                if user_input == "":
                    print("엔터 키가 입력되어 작업을 종료합니다.")
                    return

            output_verify_path = target_dir / f"{display_name}_검수.pdf"

            print(f"\n🔄 짝 맞춤 성공: [{pairs['jul'].name}] 🤝 [{pairs['yaboot'].name}]")
            merge_lecture_notes(
                str(pairs['jul']),
                str(pairs['yaboot']),
                str(output_main_path),
                str(output_verify_path)
            )
            processed_count += 1

        elif 'jul' in pairs:
            print(f"⚠️ '{pairs['jul'].name}' 파일이 있지만 매칭되는 야붙 파일이 없습니다.")
        elif 'yaboot' in pairs:
            print(f"⚠️ '{pairs['yaboot'].name}' 파일이 있지만 매칭되는 줄필기 파일이 없습니다.")

    print("="*50)
    print(f"🎉 총 {processed_count}개의 세트 병합이 완료되었습니다.")


if __name__ == "__main__":
    # 소스(_jul, _yaboot)는 lecture 하위 폴더에 모아두고,
    # 병합 결과물(메인 + 검수 파일)은 2026-1 최상위에 생성.

    TARGET_FOLDER = WATCH_PATH + r"\lecture"
    OUTPUT_FOLDER = WATCH_PATH
    process_all_files_in_directory(TARGET_FOLDER, OUTPUT_FOLDER)