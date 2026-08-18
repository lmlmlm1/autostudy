import os
import re
import json
import io
import fitz  # PyMuPDF
from xhtml2pdf import pisa
import markdown
from dotenv import load_dotenv
from pylatexenc.latex2text import LatexNodes2Text  # 수식 변환용 라이브러리 추가

load_dotenv()

# 좆버그 방지용
from xhtml2pdf import pisa, default
from xhtml2pdf.default import DEFAULT_CSS
from xhtml2pdf.files import pisaFileObject
# patch background color/image bleeding into other elements
#default.DEFAULT_CSS = DEFAULT_CSS.replace("background-color: transparent;", "", 1)


def append_scripts_to_pdf(base_name: str):
    # 1. 환경 변수에서 WATCH_PATH 가져오기 및 경로 설정
    watch_path = os.environ.get("WATCH_PATH")
    if not watch_path:
        raise ValueError("환경 변수 'WATCH_PATH'가 설정되지 않았습니다.")

    target_dir = os.path.join(watch_path, base_name)
    
    pdf_path = os.path.join(target_dir, f"{base_name}.pdf")
    json_path = os.path.join(target_dir, f"{base_name}_done.json") # 업로드하신 파일명에 맞춤
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

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    mac_font_path = os.path.join(BASE_DIR, "fonts", "apple-gothic.ttf")
    # patch temporary file resolution when loading fonts, 좆버그 방지용
    pisaFileObject.getNamedFile = lambda self: self.uri

    # 5. 공통 CSS 정의 (순서도가 들어가는 pre 태그 스타일 대폭 수정)
    common_css = f"""
        @font-face {{
            font-family: 'KoreanFont';
            src: url('{mac_font_path}');
        }}
        body {{
            font-family: 'KoreanFont', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: #1d1d1f;
            word-wrap: cjk; 
            word-break: keep-all;
        }}
        
        /* [핵심 수정] 순서도가 깨지지 않도록 코드 블록 최적화 */
        pre {{
            font-family: 'KoreanFont', monospace;
            font-size: 7.5pt; /* 가로로 긴 순서도가 한 줄에 들어가도록 크기 축소 */
            line-height: 1.2;
            white-space: pre; /* 엔진이 마음대로 줄바꿈 하는 것을 금지 */
            background-color: #f4f5f7;
            padding: 10px;
            border: 1pt solid #ddd;
        }}
        code {{
            font-family: 'KoreanFont', monospace;
        }}

        h1 {{ font-size: 18pt; color: #000; border-bottom: 1.5pt solid #333; padding-bottom: 5px; margin-bottom: 15px; -pdf-keep-with-next: true; }}
        h2 {{ font-size: 14pt; color: #222; margin-top: 15px; margin-bottom: 10px; border-bottom: 0.5pt solid #ccc; -pdf-keep-with-next: true; }}
        h3 {{ font-size: 12pt; color: #333; margin-top: 12px; margin-bottom: 8px; -pdf-keep-with-next: true; }}
        p {{ margin-bottom: 8px; text-align: justify; }}
        
        ul {{ margin-bottom: 10pt; margin-left: 25pt; list-style-type: disc; }}
        ul ul {{ margin-bottom: 0; margin-left: 20pt; list-style-type: circle; }}
        ol {{ margin-bottom: 10pt; margin-left: 25pt; list-style-type: decimal; }}
        li {{ margin-bottom: 5pt; padding-left: 2pt; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
        th, td {{ border: 0.5pt solid #999; padding: 8px; text-align: left; vertical-align: top; }}
        th {{ background-color: #f0f0f0; font-weight: bold; text-align: center; }}
        strong, b {{ font-weight: bold; color: #000; }}
    """

    # 마크다운 전처리 함수 (개선된 로직 적용)
    def preprocess_markdown(text):
        if not text:
            return text
            
        # 1. 수식 블록($...$) 구조를 활용하여 수식 기호를 안전하게 치환 (파서 에러 방지 포함)
        def convert_math_block(match):
            math_expr = match.group(1)
            
            # 파서를 고장내는 주범(\ + 공백)을 변환기 작동 '전'에 미리 청소
            math_expr = re.sub(r'\\(\s+)', r'\1', math_expr)
            
            try:
                # 깔끔해진 수식을 유니코드로 정상 변환
                converted = LatexNodes2Text(math_mode=True).latex_to_text(math_expr)
            except Exception:
                # 최악의 경우 파서가 뻗더라도 가장 중요한 기호는 살려내는 2중 안전망
                converted = math_expr.replace(r'\times', '×').replace(r'\le', '≤').replace(r'\ge', '≥')
                converted = converted.replace('\\', '')
                
            return converted

        # 수식 블록 찾기 (수식 내부만 치환하고 일반 텍스트는 보호)
        text = re.sub(r'\$\$(.*?)\$\$', convert_math_block, text, flags=re.DOTALL)
        text = re.sub(r'\$(.*?)\$', convert_math_block, text, flags=re.DOTALL)
        
        # 2. xhtml2pdf를 패닉에 빠트리는 특수 궤선/화살표 기호 안전하게 치환
        text = text.replace('──►', '-->') 
        text = text.replace('►', '>')
        text = text.replace('▼', 'v')
        text = text.replace('┌', '+').replace('┐', '+').replace('└', '+').replace('┘', '+')
        text = text.replace('├', '+').replace('┤', '+').replace('┬', '+').replace('┴', '+')
        text = text.replace('│', '|').replace('─', '-')

        # 3. 리스트 여백 강제 확보
        text = re.sub(r'([^\n])\n(\s*[\*\-]\s)', r'\1\n\n\2', text)
        
        return text

    # --- [Phase 1] Summary & Terms ---
    if summary or terms:
        md_summary = f"{summary}\n\n---\n\n{terms}" if summary and terms else f"{summary}{terms}"
        
        md_summary = preprocess_markdown(md_summary)
        html_summary_body = markdown.markdown(md_summary, extensions=['tables', 'sane_lists', 'fenced_code'])
        
        summary_html = f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><style>
            {common_css}
            @page {{
                size: a4 portrait;
                margin: 40pt;
            }}
        </style></head>
        <body>
            {html_summary_body}
        </body></html>
        """
        
        summary_pdf_io = io.BytesIO()
        pisa.CreatePDF(io.StringIO(summary_html), dest=summary_pdf_io)
        summary_doc = fitz.open("pdf", summary_pdf_io.getvalue())
        out_doc.insert_pdf(summary_doc)
        summary_doc.close()

    # --- [Phase 2] Slides & Scripts ---
    for page_index in range(len(orig_doc)):
        slide_num = page_index + 1
        raw_text = slides_data.get(slide_num, "").strip()

        if not raw_text or raw_text == "(내용 없음)":
            new_page = out_doc.new_page(width=a4_width, height=a4_height)
            new_page.show_pdf_page(top_half_rect, orig_doc, page_index)
            continue

        raw_text = preprocess_markdown(raw_text)
        html_script_body = markdown.markdown(raw_text, extensions=['tables', 'sane_lists', 'fenced_code'])

        script_html = f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><style>
            {common_css}
            @page {{
                size: a4 portrait;
                margin-top: 430pt;
                margin-bottom: 40pt;
                margin-left: 40pt;
                margin-right: 40pt;
            }}
        </style></head>
        <body>
            {html_script_body}
        </body></html>
        """

        script_pdf_io = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.StringIO(script_html), dest=script_pdf_io)
        
        if pisa_status.err:
            print(f"Slide {slide_num} 텍스트 변환 중 오류 발생")
            continue

        temp_doc = fitz.open("pdf", script_pdf_io.getvalue())
        
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
    # 전달해주신 파일명에 맞게 실행부 수정
    append_scripts_to_pdf("0521_34")