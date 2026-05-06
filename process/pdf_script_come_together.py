import os
import re
import json
import io
import fitz  # PyMuPDF
from xhtml2pdf import pisa  # 원래 쓰시던 근본 라이브러리로 복귀!

def append_scripts_to_pdf(base_name: str):
    # 1. 메인에서 했으니 여긴 그냥 써도 됨
    # 감시할 구글 드라이브 로컬 경로
    WATCH_PATH = os.getenv("WATCH_PATH")

    # 2. WATCH_PATH 에서 검색
    result_json_path = os.path.join(WATCH_PATH, f"{base_name}_result.json")
    pdf_path = os.path.join(WATCH_PATH, f"{base_name}.pdf")
    out_pdf_path = os.path.join(WATCH_PATH, f"{base_name}_scripted.pdf")

    # 파일 존재 여부 확인
    if not os.path.exists(pdf_path):
        print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return
    if not os.path.exists(result_json_path):
        print(f"JSON 파일을 찾을 수 없습니다: {result_json_path}")
        return

    # 3. JSON 데이터 로드
    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    corrected_text = data.get("corrected_text", "")
    summary = data.get("summary", "")
    terms = data.get("terms", "")

    # 4. [Slide 001] 등의 패턴을 정규식으로 파싱
    pattern = r'\[Slide\s+(\d+)\](.*?)(?=\[Slide\s+\d+\]|$)'
    slides_data = {}
    for match in re.finditer(pattern, corrected_text, re.DOTALL | re.IGNORECASE):
        slide_idx = int(match.group(1))
        text = match.group(2).strip()
        slides_data[slide_idx] = text

    # 5. 원본 PDF 열기 및 출력용 빈 문서 생성
    orig_doc = fitz.open(pdf_path)
    out_doc = fitz.Document()

    a4_width = 595.0
    a4_height = 842.0
    top_half_rect = fitz.Rect(0, 0, a4_width, a4_height / 2)

    # macOS 기본 한글 폰트 경로 (xhtml2pdf는 ttf 확장자를 선호합니다)
    mac_font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

    # **텍스트** 패턴을 정석적인 HTML <b> <i> 태그로 치환하는 함수
    def replace_markdown_bold(text):
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    def replace_markdown_itlaic(text):
        return re.sub(r'\*(.*?)\*', r'<i>\1</i>', text, flags=re.DOTALL)

    # 7. 페이지 순회하며 합성
    for page_index in range(len(orig_doc)):
        slide_num = page_index + 1
        raw_text = slides_data.get(slide_num, "").strip()

        # 내용이 없을 경우 원본 슬라이드만 상단에 배치하고 패스
        if not raw_text or raw_text == "(내용 없음)":
            new_page = out_doc.new_page(width=a4_width, height=a4_height)
            new_page.show_pdf_page(top_half_rect, orig_doc, page_index)
            continue

        comment_text = raw_text.replace('\n', '<br>')
        comment_text = replace_markdown_bold(comment_text)
        comment_text = replace_markdown_itlaic(comment_text)

        extra_info = ""
        if slide_num == 1 and (summary or terms):
            s_html = replace_markdown_bold(summary.replace('\n', '<br>'))
            t_html = replace_markdown_bold(terms.replace('\n', '<br>'))
            extra_info = f"""
            <div class="summary-box">
                <p>{s_html}</p>
                <p>{t_html}</p>
            </div>
            """

        # xhtml2pdf를 위한 HTML 포맷 (핵심은 @page의 margin-top!)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            @font-face {{
                font-family: 'KoreanFont';
                src: url('{mac_font_path}');
            }}
            @page {{
                size: a4 portrait;
                /* A4 높이의 절반 아래부터 텍스트가 시작되도록 상단 여백을 강제로 줍니다 */
                margin-top: 430pt;   
                margin-bottom: 40pt;
                margin-left: 40pt;
                margin-right: 40pt;
            }}
            body {{
                font-family: 'KoreanFont', sans-serif;
                font-size: 10pt;
                line-height: 1.6;
                color: #1d1d1f;
            }}
            .summary-box {{
                background-color: #f5f5f7;
                padding: 12px;
                margin-bottom: 20px;
            }}
            b {{
                color: #000000;
            }}
        </style>
        </head>
        <body>
            {extra_info}
            <div class="script-content">{comment_text}</div>
        </body>
        </html>
        """

        # A. xhtml2pdf를 통해 HTML을 하단 영역에만 텍스트가 있는 임시 PDF로 변환
        pdf_bytes_io = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_bytes_io)
        
        if pisa_status.err:
            print(f"Slide {slide_num} 텍스트 변환 중 오류 발생")
            continue

        # B. 방금 만든 임시 PDF 문서를 메모리에서 열기
        temp_doc = fitz.open("pdf", pdf_bytes_io.getvalue())
        
        # C. 하단에 스크립트가 적힌 각 페이지의 텅 빈 상단에 원본 슬라이드 찍어내기
        for temp_page in temp_doc:
            temp_page.show_pdf_page(top_half_rect, orig_doc, page_index)
        
        # D. 최종 문서에 병합
        out_doc.insert_pdf(temp_doc)
        temp_doc.close()

    # 8. 최종 결과물 저장
    out_doc.save(out_pdf_path)
    out_doc.close()
    orig_doc.close()
    
    print(f"작업 완료: {out_pdf_path} 파일이 성공적으로 생성되었습니다.")

if __name__ == "__main__":
    # 스크립트 단독 실행 시 테스트를 위한 환경 변수 세팅 (필요 시 주석 해제하여 사용)
    # os.environ["WATCH_PATH"] = "/Users/내계정/Documents/PDF_Work"
    
    append_scripts_to_pdf("0428_1")