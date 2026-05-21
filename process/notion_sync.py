import os
import json
import re
import time
import yt_dlp
from notion_client import Client
from upload.google_drive import get_drive_file_url

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID") 
data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")
WATCH_PATH = os.getenv("WATCH_PATH")
YOUTUBE_PLAYLIST_URL = os.getenv("YOUTUBE_PLAYLIST_URL")

# --- 1. 유틸리티 함수 ---

# 🌟 수정된 함수 1: 볼드체(**)뿐만 아니라 기울임꼴(*)과 볼드+기울임(***)까지 완벽 지원
def convert_text_to_notion_rich_text(text):
    # ***bold italic***, **bold**, *italic* 을 순서대로 캡처하는 정규식
    parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)', text)
    rich_text_list = []
    
    for part in parts:
        if not part: 
            continue
            
        is_bold = False
        is_italic = False
        content = part
        
        # 기호 패턴에 따라 서식 및 순수 텍스트 내용 분리
        if part.startswith("***") and part.endswith("***") and len(part) >= 6:
            is_bold = True
            is_italic = True
            content = part[3:-3]
        elif part.startswith("**") and part.endswith("**") and len(part) >= 4:
            is_bold = True
            content = part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
            is_italic = True
            content = part[1:-1]
            
        if not content:
            continue
            
        # 2000자 제한 쪼개기 처리
        for j in range(0, len(content), 2000):
            chunk = content[j:j+2000]
            rt_obj = {
                "type": "text",
                "text": {"content": chunk}
            }
            
            # 노션 서식(annotations) 조립
            annotations = {}
            if is_bold:
                annotations["bold"] = True
            if is_italic:
                annotations["italic"] = True
                
            if annotations:
                rt_obj["annotations"] = annotations
            
            rich_text_list.append(rt_obj)
            
    return rich_text_list

# 기존 import문 아래에 정규식 매칭을 위한 re가 이미 있을 것입니다.

# 🌟 추가 함수 1: 해당 라인이 마크다운 표의 구분선인지 확인하는 함수
def is_separator_line(line):
    if not line.startswith('|') or not line.endswith('|'):
        return False
    # | :--- | --- | 같은 형태에서 안쪽 기호들만 추출
    cells = [c.strip() for c in line.split('|')][1:-1]
    if not cells:
        return False
    # 모든 셀이 하이픈(-)과 콜론(:)으로만 이루어져 있는지 확인
    return all(re.match(r'^:?-+:?$', c) for c in cells)

# 🌟 추가 함수 2: 수집된 표 텍스트를 노션 Table 블록 객체로 변환하는 함수
def parse_markdown_table(table_lines):
    has_header = False
    parsed_rows = []
    
    for line in table_lines:
        if is_separator_line(line):
            has_header = True
            continue
        
        # 양 끝의 |를 제거하고 각 셀의 텍스트 추출
        cells = [cell.strip() for cell in line.split('|')][1:-1]
        if cells:
            parsed_rows.append(cells)
        
    if not parsed_rows:
        return None
        
    # 가장 긴 행을 기준으로 열(Column) 개수 계산
    table_width = max(len(row) for row in parsed_rows)
    
    children_rows = []
    for row in parsed_rows:
        # 열 개수가 부족한 행이 있다면 빈 문자열로 패딩 처리
        while len(row) < table_width:
            row.append("")
            
        cells_json = []
        for cell in row:
            # 셀 내부 텍스트에도 볼드체(**) 등이 적용되도록 처리
            cells_json.append(convert_text_to_notion_rich_text(cell))
            
        children_rows.append({
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": cells_json
            }
        })
        
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": table_width,
            "has_column_header": has_header,
            "has_row_header": False,
            "children": children_rows
        }
    }

# 🌟 수정된 메인 파서 함수: 표(Table) 감지 로직이 통합됨
def create_markdown_blocks(text):
    blocks = []
    # 공백 라인을 무조건 지우지 않고 배열에 유지하여 여백을 살립니다.
    lines = [line.strip() for line in text.split('\n')]

    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 1. 빈 줄 처리 (노션의 빈 paragraph 블록으로 문단 간 여백 확보)
        if not line:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": []}
            })
            i += 1
            continue
            
        # 2. 마크다운 구분선(---) 처리
        if line == "---":
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            i += 1
            continue

        # 3. 마크다운 표(Table) 구조 감지
        is_table = False
        header_index = -1
        
        if line.startswith('|'):
            if i + 1 < len(lines) and is_separator_line(lines[i+1]):
                is_table = True
                header_index = i
            elif i + 2 < len(lines) and is_separator_line(lines[i+2]) and lines[i+1].startswith('|'):
                is_table = True
                header_index = i + 1
                title_content = line.lstrip('|').strip()
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": convert_text_to_notion_rich_text(title_content)}
                })
        
        if is_table:
            table_lines = []
            table_lines.append(lines[header_index])    
            table_lines.append(lines[header_index+1])  
            
            idx = header_index + 2
            while idx < len(lines) and lines[idx].startswith('|') and not is_separator_line(lines[idx]):
                table_lines.append(lines[idx])
                idx += 1
                
            table_block = parse_markdown_table(table_lines)
            if table_block:
                blocks.append(table_block)
                
            i = idx  
            continue

        # 4. 일반 마크다운 블록 처리 (제목, 리스트 등)
        block_type = "paragraph"
        content = line

        if line.startswith("### "):
            block_type = "heading_3"
            content = line[4:]
        elif line.startswith("## "):
            block_type = "heading_2"
            content = line[3:]
        elif line.startswith("# "):
            block_type = "heading_1"
            content = line[2:]
        elif line.startswith("* ") or line.startswith("- "):
            block_type = "bulleted_list_item"
            content = line[2:]

        rich_text_list = convert_text_to_notion_rich_text(content)
        blocks.append({
            "object": "block",
            "type": block_type,
            block_type: {"rich_text": rich_text_list}
        })
        i += 1
            
    return blocks

def get_youtube_urls_from_playlist(playlist_url, target_prefix):
    if not playlist_url:
        return []
    
    print(f"🔍 [YouTube] 재생목록에서 '{target_prefix}'로 시작하는 영상 검색 중...")
    ydl_opts = {
        'extract_flat': True,
        'quiet': True
    }
    
    matched_urls = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            for entry in info.get('entries', []):
                title = entry.get('title', '')
                if title.startswith(target_prefix):
                    matched_urls.append(entry.get('url'))
    except Exception as e:
        print(f"⚠️ 유튜브 재생목록 검색 실패: {e}")
        
    return matched_urls

# --- 2. 메인 업로드 함수 ---

def trigger_notion_upload(base_name):
    target_dir = os.path.join(WATCH_PATH, base_name)
    result_json_path = os.path.join(target_dir, f"{base_name}_result.json")
    if not os.path.exists(result_json_path): return

    print(f"🚀 [Notion 팀] '{base_name}' 업로드 준비...")
    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pdf_url = get_drive_file_url(f"{base_name}.pdf")
    
    properties = {
        "이름": {"title": [{"text": {"content": f"📖 {base_name}"}}]},
        "원본 PDF": {"url": pdf_url if pdf_url else None},
        "상태": {"select": {"name": "✅ 완료"}}
    }

    children = []
    
    # 토글 목차 추가
    children.append({
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": "📑 목차 보기"}}],
            "children": [
                {"object": "block", "type": "table_of_contents", "table_of_contents": {}}
            ]
        }
    })
    children.append({"object": "block", "type": "divider", "divider": {}})

    # 유튜브 영상 추가
    youtube_urls = get_youtube_urls_from_playlist(YOUTUBE_PLAYLIST_URL, base_name)
    
    if youtube_urls:
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📺 강의 영상"}}]}})
        for url in youtube_urls:
            children.append({
                "object": "block", 
                "type": "video", 
                "video": {"type": "external", "external": {"url": url}}
            })
            
    # 핵심 요약 추가
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📌 핵심 요약"}}]}})
    children.extend(create_markdown_blocks(data["summary"]))

    # 슬라이드 스크립트 추가
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📝 슬라이드 스크립트"}}]}})
    
    slides_data = re.split(r'\[Slide (\d+)\]', data["corrected_text"])
    
    for i in range(1, len(slides_data), 2):
        slide_num = slides_data[i]
        formatted_num = str(slide_num).zfill(3) 
        slide_content = slides_data[i+1].strip()
        img_filename = f"{base_name}_{formatted_num}.png"
        
        children.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": f"🖥️ Slide {formatted_num}"}}]}})
        
        img_url = get_drive_file_url(img_filename)
        if img_url:
            file_id_match = re.search(r'[-\w]{25,}', img_url)
            if file_id_match:
                actual_id = file_id_match.group() 
                direct_img_url = f"https://drive.google.com/thumbnail?id={actual_id}&sz=w2000"
                children.append({
                    "object": "block", 
                    "type": "image", 
                    "image": {"type": "external", "external": {"url": direct_img_url}}
                })
        
        if slide_content and slide_content != "(내용 없음)":
            children.extend(create_markdown_blocks(slide_content))
        
        children.append({"object": "block", "type": "divider", "divider": {}})

    try:
        created_page = notion.pages.create(parent={"database_id": database_id}, properties=properties)
        page_id = created_page["id"]
        
        chunk_size = 100
        for i in range(0, len(children), chunk_size):
            chunk = children[i:i + chunk_size]
            notion.blocks.children.append(block_id=page_id, children=chunk)
            time.sleep(0.3) 
            
        print(f"✅ [Notion] '{base_name}' 업로드 성공!")
        os.rename(result_json_path, os.path.join(target_dir, f"{base_name}_done.json"))
            
    except Exception as e:
        print(f"❌ [Notion] 업로드 실패: {e}")

# --- 3. 기존 Anki 링크 업데이트 함수 (복구됨) ---

def append_anki_links_to_notion(base_name):
    print(f"\n🔗 [Notion 팀] '📖 {base_name}' 기존 페이지를 찾아 Anki 링크를 덧붙입니다...")
    
    apkg_url = get_drive_file_url(f"{base_name}_통합본.apkg")
    basic_csv_url = get_drive_file_url(f"{base_name}_Basic.csv")
    mcq_csv_url = get_drive_file_url(f"{base_name}_MCQ.csv")
    cloze_csv_url = get_drive_file_url(f"{base_name}_Cloze.csv")
    
    if not any([apkg_url, basic_csv_url, mcq_csv_url, cloze_csv_url]):
        print("⚠️ 덧붙일 Anki 파일(링크)을 찾을 수 없습니다.")
        time.sleep(5)
        apkg_url = get_drive_file_url(f"{base_name}_통합본.apkg")
        basic_csv_url = get_drive_file_url(f"{base_name}_Basic.csv")
        mcq_csv_url = get_drive_file_url(f"{base_name}_MCQ.csv")
        cloze_csv_url = get_drive_file_url(f"{base_name}_Cloze.csv")

    try:
        response = notion.data_sources.query(
            **{
                "data_source_id": data_source_id,
                "filter": {
                    "property": "이름",
                    "rich_text": {
                        "contains": f"📖 {base_name}",
                    },
                },
            }
        )
        
        if not response.get("results"):
            print(f"❌ 일치하는 노션 페이지를 찾을 수 없습니다. (검색어: 📖 {base_name})")
            return
            
        page_id = response["results"][0]["id"]
        
        children = []
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "🗂️ 실전 복습용 Anki 덱 다운로드"}}]}})
        if apkg_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 통합 덱 다운로드", "link": {"url": apkg_url}}, "annotations": {"bold": True, "color": "red"}}]}})
        if basic_csv_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 Basic (핵심 문답) 카드 다운로드", "link": {"url": basic_csv_url}}, "annotations": {"bold": True, "color": "blue"}}]}})
        if mcq_csv_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 MCQ (객관식) 카드 다운로드", "link": {"url": mcq_csv_url}}, "annotations": {"bold": True, "color": "purple"}}]}})
        if cloze_csv_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 Cloze (빈칸 뚫기) 카드 다운로드", "link": {"url": cloze_csv_url}}, "annotations": {"bold": True, "color": "green"}}]}})
            
        notion.blocks.children.append(
            block_id=page_id,
            children=children
        )
        print("✅ [Notion 팀] 기존 페이지 맨 아래에 Anki 다운로드 링크 덧붙이기 성공!")
        
    except Exception as e:
        print(f"❌ Notion 페이지 업데이트 실패: {e}")