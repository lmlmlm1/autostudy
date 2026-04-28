import os
import json
from notion_client import Client
#구글드라이브
from upload.google_drive import get_drive_file_url

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID") 
data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")

import re
# 볼드체 처리
def convert_text_to_notion_rich_text(text):
    parts = re.split(r'\*\*(.*?)\*\*', text)
    rich_text_list = []
    
    for i, part in enumerate(parts):
        if not part: 
            continue
            
        is_bold = (i % 2 == 1) # 홀수 인덱스는 ** 로 감싸진 부분
        
        # 만약 볼드체나 일반 텍스트 조각 자체가 2000자를 넘는다면 2000자씩 쪼개기
        for j in range(0, len(part), 2000):
            chunk = part[j:j+2000]
            rt_obj = {
                "type": "text",
                "text": {"content": chunk}
            }
            if is_bold:
                rt_obj["annotations"] = {"bold": True}
            
            rich_text_list.append(rt_obj)
            
    return rich_text_list

# 🌟 수정된 함수 2: 노션 API 제한(객체 100개 & 글자 2000자)을 모두 만족하도록 블록 생성
def create_rich_text_blocks(text, block_type="paragraph", split_by_newline=True):
    blocks = []
    
    # 옵션에 따라 줄바꿈 처리
    if split_by_newline:
        sections = [p.strip() for p in text.split('\n') if p.strip()]
    else:
        sections = [text.strip()] if text.strip() else []

    for section in sections:
        if not section:
            continue
            
        # 1. 텍스트를 통째로 변환 (마크다운 깨짐 방지)
        rich_text_list = convert_text_to_notion_rich_text(section)
        
        current_rich_text = []
        current_length = 0
        
        # 2. 객체를 순회하며 100개 제한 & 2000자 제한에 맞춰 블록 분할
        for rt in rich_text_list:
            content_len = len(rt["text"]["content"])
            
            # [핵심 로직] 현재 배열이 100개가 되거나, 다음 텍스트를 더했을 때 2000자를 넘기면 블록 생성
            if len(current_rich_text) >= 100 or current_length + content_len > 2000:
                blocks.append({
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": current_rich_text
                    }
                })
                current_rich_text = [] # 초기화
                current_length = 0
            
            # 배열에 추가
            current_rich_text.append(rt)
            current_length += content_len
            
        # 3. 마지막에 남은 객체들 처리
        if current_rich_text:
            blocks.append({
                "object": "block",
                "type": block_type,
                block_type: {
                    "rich_text": current_rich_text
                }
            })
            
    return blocks
    
def trigger_notion_upload(base_name):
    target_dir = os.path.join(WATCH_PATH, base_name)
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

def append_anki_links_to_notion(base_name):
    print(f"\n🔗 [Notion 팀] '📖 {base_name}' 기존 페이지를 찾아 Anki 링크를 덧붙입니다...")
    
    # 1. 구글 드라이브에서 생성된 Anki CSV 파일들의 링크를 가져옵니다.
    basic_csv_url = get_drive_file_url(f"{base_name}_Basic.csv")
    mcq_csv_url = get_drive_file_url(f"{base_name}_MCQ.csv")
    cloze_csv_url = get_drive_file_url(f"{base_name}_Cloze.csv")
    
    if not any([basic_csv_url, mcq_csv_url, cloze_csv_url]):
        print("⚠️ 덧붙일 Anki 파일(링크)을 찾을 수 없습니다.")
        return

    try:
        # 2. 노션 데이터베이스 검색: "이름" 속성이 "📖 base_name"과 똑같은 페이지를 찾습니다.
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
        
        # 페이지가 없으면 종료
        if not response.get("results"):
            print(f"❌ 일치하는 노션 페이지를 찾을 수 없습니다. (검색어: 📖 {base_name})")
            return
            
        # 검색된 첫 번째 페이지의 고유 ID를 가져옵니다.
        page_id = response["results"][0]["id"]
        
        # 3. 페이지 맨 아래에 덧붙일 블록(Children)들을 조립합니다.
        children = []
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "🗂️ 실전 복습용 Anki 덱 다운로드"}}]}})
        
        if basic_csv_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 Basic (핵심 문답) 카드 다운로드", "link": {"url": basic_csv_url}}, "annotations": {"bold": True, "color": "blue"}}]}})
        if mcq_csv_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 MCQ (객관식) 카드 다운로드", "link": {"url": mcq_csv_url}}, "annotations": {"bold": True, "color": "purple"}}]}})
        if cloze_csv_url:
            children.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "📥 Cloze (빈칸 뚫기) 카드 다운로드", "link": {"url": cloze_csv_url}}, "annotations": {"bold": True, "color": "green"}}]}})
            
        # 4. 찾은 페이지(page_id)의 자식 블록으로 새 블록들을 밀어 넣습니다.
        notion.blocks.children.append(
            block_id=page_id,
            children=children
        )
        print("✅ [Notion 팀] 기존 페이지 맨 아래에 Anki 다운로드 링크 덧붙이기 성공!")
        
    except Exception as e:
        print(f"❌ Notion 페이지 업데이트 실패: {e}")