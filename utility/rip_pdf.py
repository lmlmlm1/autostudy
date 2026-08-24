import os
from pypdf import PdfReader, PdfWriter

# ==========================================
# ⚙️ 1. 파일 경로 설정
# ==========================================
pdf_a = r"G:\내 드라이브\2026-1\lecture\0820_1.pdf"
#pdf_b = r"G:\내 드라이브\2026-1\doc_b.pdf"
#pdf_c = r"G:\내 드라이브\2026-1\doc_c.pdf"
output_pdf = r"G:\내 드라이브\2026-1\0820_2.pdf"

# ==========================================
# ⚙️ 2. 작업 지시서 작성
# 형식: (파일변수, 시작페이지, 끝페이지) — 1부터 시작하는 실제 페이지 번호 기준
# ==========================================
tasks = [
    (pdf_a, 11, 100),
    #(pdf_b, 3, 3),
    #(pdf_a, 10, 15),
    #(pdf_c, 2, 8),
]

print("📄 복합 PDF 병합을 시작합니다...")

# --------------------------------------------------
# 사전 체크: 이 작업 목록에서 실제로 쓰이는 파일들이
# 전부 존재하는지 먼저 확인 (구글 드라이브 미동기화 등 대비)
# --------------------------------------------------
unique_paths = {path for path, _, _ in tasks}
missing = [p for p in unique_paths if not os.path.exists(p)]
if missing:
    print("❌ 다음 파일을 찾을 수 없습니다. 경로 또는 동기화 상태를 확인하세요:")
    for p in missing:
        print(f"   - {p}")
    raise SystemExit(1)

writer = PdfWriter()
readers_cache = {}

def get_reader(path):
    """캐시에 없으면 열어서 저장. 손상된 PDF 등 예외 상황 처리."""
    if path not in readers_cache:
        try:
            readers_cache[path] = PdfReader(path)
        except Exception as e:
            print(f"❌ '{os.path.basename(path)}' 파일을 여는 중 오류 발생: {e}")
            raise SystemExit(1)
    return readers_cache[path]

for path, start_page, end_page in tasks:
    reader = get_reader(path)
    total_pages = len(reader.pages)

    # start_page > end_page (순서 역전) 감지
    if start_page > end_page:
        print(f"⚠️ 경고: '{os.path.basename(path)}' 작업의 페이지 범위가 역전되어 있습니다 "
              f"({start_page} > {end_page}). 이 작업은 건너뜁니다.")
        continue

    # 범위를 실제 페이지 수에 맞게 한 번만 클램핑
    clamped_end = min(end_page, total_pages)
    if clamped_end < end_page:
        print(f"⚠️ 경고: '{os.path.basename(path)}' 파일은 {total_pages}페이지까지만 있습니다. "
              f"({start_page}~{end_page} 요청 → {start_page}~{clamped_end}로 조정)")

    if start_page > total_pages:
        print(f"⚠️ 경고: '{os.path.basename(path)}'에 {start_page}페이지가 없어 이 작업은 건너뜁니다.")
        continue

    for i in range(start_page - 1, clamped_end):
        writer.add_page(reader.pages[i])

# --------------------------------------------------
# 출력 폴더 없으면 생성
# --------------------------------------------------
output_dir = os.path.dirname(output_pdf)
if output_dir:
    os.makedirs(output_dir, exist_ok=True)

if len(writer.pages) == 0:
    print("❌ 병합할 페이지가 하나도 없습니다. tasks 목록을 확인하세요.")
    raise SystemExit(1)

with open(output_pdf, "wb") as f:
    writer.write(f)

# 파일 핸들 정리
for reader in readers_cache.values():
    try:
        reader.stream.close()
    except Exception:
        pass

print(f"✅ 커스텀 병합 완료: '{output_pdf}' 파일이 생성되었습니다. (총 {len(writer.pages)}페이지)")