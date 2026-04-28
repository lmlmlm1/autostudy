import os
import json
import re
import time
from notion_client import Client
from upload.google_drive import get_drive_file_url

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID") 

def convert_text_to_notion_rich_text(text):
    parts = re.split(r'\*\*(.*?)\*\*', text)
    rich_text_list = []
    for i, part in enumerate(parts):
        if not part: continue
        if i % 2 == 1:
            rich_text_list.append({"type": "text", "text": {"content": part}, "annotations": {"bold": True}})
        else:
            rich_text_list.append({"type": "text", "text": {"content": part}})
    return rich_text_list

def create_rich_text_blocks(text, block_type="paragraph", max_length=2000, split_by_newline=True):
    blocks = []
    sections = [p.strip() for p in text.split('\n') if p.strip()] if split_by_newline else [text.strip()] if text.strip() else []
    for section in sections:
        chunks = [section[i:i+max_length] for i in range(0, len(section), max_length)]
        for chunk in chunks:
            blocks.append({"object": "block", "type": block_type, block_type: {"rich_text": convert_text_to_notion_rich_text(chunk)}})
    return blocks

def trigger_notion_upload(base_name, target_dir):
    result_json_path = os.path.join(target_dir, f"{base_name}_result.json")
    if not os.path.exists(result_json_path): return

    print(f"🚀 [Notion 팀] '{base_name}' 업로드 준비...")
    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    media_url = get_drive_file_url(f"{base_name}.mp4") or get_drive_file_url(f"{base_name}.mp3")
    pdf_url = get_drive_file_url(f"{base_name}.pdf")
    
    video_path = os.path.join(target_dir, f"{base_name}.mp4")
    is_video = os.path.exists(video_path)
    block_type = "video" if is_video else "audio"

    properties = {
        "이름": {"title": [{"text": {"content": f"📖 {base_name}"}}]},
        "원본 PDF": {"url": pdf_url if pdf_url else None},
        "강의 영상": {"url": media_url if media_url else None},
        "상태": {"select": {"name": "✅ 완료"}}
    }

    children = []
    # 목차 추가
    children.append({"object": "block", "type": "table_of_contents", "table_of_contents": {}})
    children.append({"object": "block", "type": "divider", "divider": {}})

    if media_url:
        embed_url = media_url.replace("/view?usp=drivesdk", "/preview")
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📺 미디어"}}]}})
        children.append({"object": "block", "type": block_type, block_type: {"type": "external", "external": {"url": embed_url}}})

    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📌 핵심 요약"}}]}})
    children.extend(create_rich_text_blocks(data["summary"], block_type="bulleted_list_item", split_by_newline=False))
    
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📑 용어 정리"}}]}})
    children.extend(create_rich_text_blocks(data["terms"], block_type="bulleted_list_item", split_by_newline=False))
    
    # ... (중략: 앞부분 로직) ...

    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📝 슬라이드 스크립트"}}]}})
    
    # 슬라이드 매핑 시작
    slides_data = re.split(r'\[Slide (\d+)\]', data["corrected_text"])
    
    for i in range(1, len(slides_data), 2):
        slide_num = slides_data[i]
        formatted_num = str(slide_num).zfill(3) 
        slide_content = slides_data[i+1].strip()
        img_filename = f"{base_name}_{formatted_num}.png"
        
        # 1. 슬라이드 제목 (Heading 2)
        children.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": f"🖥️ Slide {formatted_num}"}}]}})
        
        # 2. 이미지 처리 (반드시 for 루프 안에 위치해야 합니다)
        img_url = get_drive_file_url(img_filename)
        if img_url:
            file_id_match = re.search(r'[-\w]{25,}', img_url)
            if file_id_match:
                actual_id = file_id_match.group() 
                # 노션이 좋아하는 고화질 썸네일 링크
                direct_img_url = f"https://drive.google.com/thumbnail?id={actual_id}&sz=w2000"
            
                children.append({
                    "object": "block", 
                    "type": "image", 
                    "image": {
                        "type": "external", 
                        "external": {"url": direct_img_url}
                    }
                })
        
        # 3. 슬라이드 텍스트 내용 추가
        if slide_content and slide_content != "(내용 없음)":
            # create_rich_text_blocks는 리스트를 반환하므로 extend 사용
            children.extend(create_rich_text_blocks(slide_content, block_type="paragraph", split_by_newline=True))
        
        # 슬라이드 간 구분을 위한 구분선
        children.append({"object": "block", "type": "divider", "divider": {}})

    # --- 여기서부터 페이지 생성 및 블록 추가 ---
    try:
        created_page = notion.pages.create(parent={"database_id": database_id}, properties=properties)
        page_id = created_page["id"]
        
        chunk_size = 100
        for i in range(0, len(children), chunk_size):
            chunk = children[i:i + chunk_size]
            notion.blocks.children.append(block_id=page_id, children=chunk)
            time.sleep(0.3) # 노션 API 속도 제한 방어
            
        print(f"✅ [Notion] '{base_name}' 업로드 성공!")
        os.rename(result_json_path, os.path.join(target_dir, f"{base_name}_done.json"))
            
    except Exception as e:
        print(f"❌ [Notion] 업로드 실패: {e}")