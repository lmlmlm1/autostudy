import os
import re
import json
import io
import fitz  # PyMuPDF
from weasyprint import HTML
import markdown
from dotenv import load_dotenv
load_dotenv()

def append_scripts_to_pdf(base_name: str):
    # 1. 환경 변수에서 WATCH_PATH 가져오기 및 경로 설정
    watch_path = os.environ.get("WATCH_PATH")
    if not watch_path:
        raise ValueError("환경 변수 'WATCH_PATH'가 설정되지 않았습니다.")

    target_dir = os.path.join(watch_path, base_name)
    
    pdf_path = os.path.join(target_dir, f"{base_name}.pdf")
    json_path = os.path.join(target_dir, f"{base_name}_done.json")
    out_pdf_path = os.path.join(target_dir, f"{base_name}_scripted.pdf")

    if not os.path.exists(pdf_path) or not os.path.exists(json_path):
        print(f"필요한 파일을 찾을 수 없습니다.\nPDF: {pdf_path}\nJSON: {json_path}")
        return

    # 2. JSON 데이터 로드
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    corrected_text = data.get("corrected_text", "")
    summary = data.get("summary", "")
    terms = data.get("terms", "")

    # 3. [Slide 001] 등의 패턴을 정규식으로 파싱
    pattern = r'\[Slide\s+(\d+)\](.*?)(?=\[Slide\s+\d+\]|$)'
    slides_data = {}
    for match in re.finditer(pattern, corrected_text, re.DOTALL | re.IGNORECASE):
        slide_idx = int(match.group(1))
        text = match.group(2).strip()
        slides_data[slide_idx] = text

    # 4. 문서 초기화
    orig_doc = fitz.open(pdf_path)
    out_doc = fitz.Document()

    a4_width = 595.0
    a4_height = 842.0
    top_half_rect = fitz.Rect(0, 0, a4_width, a4_height / 2)

    mac_font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

    # 5. WeasyPrint용 공통 CSS (순서도 깨짐 및 글자 어긋남 방지 코드 강화)
    common_css = f"""
        @font-face {{
            font-family: 'KoreanFont';
            src: url('{mac_font_path}');
        }}
        @page {{
            size: A4 portrait;
            margin: 40pt;
        }}
        body {{
            font-family: 'KoreanFont', 'Apple SD Gothic Neo', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: #1d1d1f;
            word-break: keep-all;
        }}
        
        /* [핵심 수정] 순서도 기호(┌ ├ │ └) 주행선 어긋남 및 자동 줄바꿈 절대 방지 */
        pre {{
            font-family: 'Menlo', 'Monaco', 'Courier New', 'KoreanFont', monospace;
            font-size: 7.0pt; 
            line-height: 1.25;
            white-space: pre !important;
            word-break: keep-all !important;
            overflow-x: visible;
            background-color: #f4f5f7;
            padding: 12pt;
            border: 1pt solid #ddd;
            border-radius: 4pt;
            letter-spacing: -0.2px; /* 자간 조정을 통해 궤선 끊어짐 방지 */
        }}
        code {{
            font-family: 'Menlo', 'Monaco', 'Courier New', 'KoreanFont', monospace;
        }}
        pre code {{
            padding: 0;
            background-color: transparent;
            white-space: pre !important;
        }}

        h1 {{ font-size: 18pt; color: #000; border-bottom: 1.5pt solid #333; padding-bottom: 5px; margin-bottom: 15px; }}
        h2 {{ font-size: 14pt; color: #222; margin-top: 15px; margin-bottom: 10px; border-bottom: 0.5pt solid #ccc; }}
        h3 {{ font-size: 12pt; color: #333; margin-top: 12px; margin-bottom: 8px; }}
        p {{ margin-bottom: 8pt; text-align: justify; }}
        
        ul {{ margin-bottom: 10pt; margin-left: 20pt; }}
        li {{ margin-bottom: 4pt; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 9pt; }}
        th, td {{ border: 0.5pt solid #999; padding: 6px; text-align: left; vertical-align: top; }}
        th {{ background-color: #f0f0f0; font-weight: bold; text-align: center; }}
    """

    # 마크다운 전처리 함수
    def preprocess_markdown(text):
        if not text:
            return text
            
        text = text.replace(r'\rightarrow', '→').replace(r'\leftarrow', '←')
        text = text.replace(r'\uparrow', '↑').replace(r'\downarrow', '↓')
        text = text.replace(r'\%', '%')

        # 수학 기호 $ 제거
        text = re.sub(r'\$([^$\n]+)\$', r'\1', text)
        
        # 리스트 여백 강제 확보
        text = re.sub(r'([^\n])\n(\s*[\*\-]\s)', r'\1\n\n\2', text)
        return text

    # --- [Phase 1] Summary & Terms ---
    if summary or terms:
        md_summary = f"{summary}\n\n---\n\n{terms}" if summary and terms else f"{summary}{terms}"
        md_summary = preprocess_markdown(md_summary)
        html_summary_body = markdown.markdown(md_summary, extensions=['tables', 'sane_lists', 'fenced_code'])
        
        summary_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{common_css}</style></head><body>{html_summary_body}</body></html>"
        
        # WeasyPrint를 활용한 PDF 렌더링
        summary_pdf_bytes = HTML(string=summary_html).write_pdf()
        summary_doc = fitz.open("pdf", summary_pdf_bytes)
        out_doc.insert_pdf(summary_doc)
        summary_doc.close()

    # --- [Phase 2] Slides & Scripts ---
    slide_css = common_css + """
        @page {
            margin-top: 430pt;
            margin-bottom: 40pt;
            margin-left: 40pt;
            margin-right: 40pt;
        }
    """
    for page_index in range(len(orig_doc)):
        slide_num = page_index + 1
        raw_text = slides_data.get(slide_num, "").strip()

        if not raw_text or raw_text == "(내용 없음)":
            new_page = out_doc.new_page(width=a4_width, height=a4_height)
            new_page.show_pdf_page(top_half_rect, orig_doc, page_index)
            continue

        raw_text = preprocess_markdown(raw_text)
        html_script_body = markdown.markdown(raw_text, extensions=['tables', 'sane_lists', 'fenced_code'])

        script_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{slide_css}</style></head><body>{html_script_body}</body></html>"

        script_pdf_bytes = HTML(string=script_html).write_pdf()
        temp_doc = fitz.open("pdf", script_pdf_bytes)
        
        for temp_page in temp_doc:
            temp_page.show_pdf_page(top_half_rect, orig_doc, page_index)
        
        out_doc.insert_pdf(temp_doc)
        temp_doc.close()

    # 6. 저장
    out_doc.save(out_pdf_path, garbage=4, deflate=True)
    out_doc.close()
    orig_doc.close()
    
    print(f"작업 완료: {out_pdf_path} 파일이 성공적으로 생성되었습니다.")

if __name__ == "__main__":
    append_scripts_to_pdf("0520_2")