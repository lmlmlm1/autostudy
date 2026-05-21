import os
import re
import json
from xhtml2pdf import pisa
import markdown

def create_combined_summary_pdf(output_filename="all_summaries_combined.pdf"):
    # 1. 환경 변수에서 WATCH_PATH 가져오기
    watch_path = os.environ.get("WATCH_PATH")
    if not watch_path:
        raise ValueError("환경 변수 'WATCH_PATH'가 설정되지 않았습니다.")

    out_pdf_path = os.path.join(watch_path, output_filename)
    mac_font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

    # 2. 공통 CSS 정의
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

    # 3. 마크다운 전처리 함수
    def preprocess_markdown(text):
        if not text:
            return text
            
        text = text.replace(r'\rightarrow', '→')
        text = text.replace(r'\leftarrow', '←')
        text = text.replace(r'\uparrow', '↑')
        text = text.replace(r'\downarrow', '↓')
        text = text.replace(r'\%', '%')
        
        text = re.sub(r'\$([^$\n]+)\$', r'\1', text)
        text = re.sub(r'([^\n])\n(\s*[\*\-]\s)', r'\1\n\n\2', text)
        return text

    # 4. WATCH_PATH 하위의 모든 _done.json 파일 경로 수집
    json_files = []
    for root, dirs, files in os.walk(watch_path):
        for file in files:
            if file.endswith("_done.json"):
                json_files.append(os.path.join(root, file))

    if not json_files:
        print("생성할 요약본 데이터(_done.json)를 찾을 수 없습니다.")
        return

    # 5. 수집된 파일 경로를 오름차순으로 완벽하게 정렬 (자연 정렬)
    # 0513_2 가 0513_10 보다 먼저 오도록 문자열 내 숫자를 인식하여 정렬합니다.
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
    json_files.sort(key=natural_sort_key)

    html_bodies = []

    # 6. 정렬된 순서대로 파일 데이터 처리
    for json_path in json_files:
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"JSON 파싱 에러 (건너뜀): {json_path}")
                continue

        summary = data.get("summary", "")
        terms = data.get("terms", "")

        if not summary and not terms:
            continue

        # 파일명 추출하여 제목으로 사용
        base_name = os.path.basename(json_path).replace("_done.json", "")
        md_summary = f"# {base_name} 요약 문서\n\n"

        if summary and terms:
            md_summary += f"{summary}\n\n---\n\n{terms}"
        else:
            md_summary += f"{summary}{terms}"
        
        md_summary = preprocess_markdown(md_summary)
        html_chunk = markdown.markdown(md_summary, extensions=['tables', 'sane_lists'])
        
        html_bodies.append(html_chunk)

    if not html_bodies:
        print("유효한 데이터가 있는 파일이 없습니다.")
        return

    # 7. 각 JSON의 요약본 사이에 <pdf:nextpage /> 를 삽입
    final_html_body = "\n<pdf:nextpage />\n".join(html_bodies)

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
        {final_html_body}
    </body></html>
    """

    # 8. 최종 HTML을 하나의 PDF 파일로 저장
    with open(out_pdf_path, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(summary_html, dest=result_file)

    if pisa_status.err:
        print("PDF 생성 중 오류가 발생했습니다.")
    else:
        print(f"작업 완료: {out_pdf_path} 파일이 성공적으로 생성되었습니다.")

if __name__ == "__main__":
    create_combined_summary_pdf()