import os
import json
from notion_client import Client
#구글드라이브
from upload.google_drive import get_drive_file_url

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID") 

# 🌟 추가된 함수: 마크다운(**)을 노션 볼드체 속성으로 변환해 줍니다.
def convert_text_to_notion_rich_text(text):
    parts = re.split(r'\*\*(.*?)\*\*', text)
    rich_text_list = []
    
    for i, part in enumerate(parts):
        if not part: 
            continue
            
        if i % 2 == 1:
            # **로 감싸진 부분은 bold: True 처리
            rich_text_list.append({
                "type": "text",
                "text": {"content": part},
                "annotations": {"bold": True}
            })
        else:
            # 일반 텍스트
            rich_text_list.append({
                "type": "text",
                "text": {"content": part}
            })
            
    return rich_text_list

# 🌟 수정된 함수: 변환 함수를 거쳐서 블록을 생성하도록 변경되었습니다.
def create_rich_text_blocks(text, block_type="paragraph", max_length=2000, split_by_newline=True):
    blocks = []
    
    # 옵션에 따라 줄바꿈으로 블록을 나눌지, 통째로 처리할지 결정합니다.
    if split_by_newline:
        sections = [p.strip() for p in text.split('\n') if p.strip()]
    else:
        # 통째로 처리할 때는 앞뒤 공백만 자르고 내부의 \n은 그대로 살려둡니다.
        sections = [text.strip()] if text.strip() else []

    for section in sections:
        # 2000자 초과 시 노션 에러를 막기 위한 청크 쪼개기
        chunks = [section[i:i+max_length] for i in range(0, len(section), max_length)]
        for chunk in chunks:
            blocks.append({
                "object": "block",
                "type": block_type,
                block_type: {
                    "rich_text": convert_text_to_notion_rich_text(chunk)
                }
            })
    return blocks


def trigger_notion_upload(base_name, target_dir):
    print(f"🚀 [Notion 팀] '{base_name}' 노션 업로드 시작...")
    
    # 1. JSON 데이터 로드
    result_json_path = os.path.join(target_dir, f"{base_name}_result.json")
    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 2. 구글 드라이브 링크 수집 (외부 함수 호출 가정)
    media_url = get_drive_file_url(f"{base_name}.mp4") or get_drive_file_url(f"{base_name}.mp3") or get_drive_file_url(f"{base_name}.m4a")
    pdf_url = get_drive_file_url(f"{base_name}.pdf")
    
    # 3. 미디어 타입 판별
    video_path = os.path.join(target_dir, f"{base_name}.mp4")
    if os.path.exists(video_path) : 
        is_video = True
    else : 
        is_video = False
    block_type = "video" if is_video else "audio"

    # 4. 데이터베이스 속성(Properties) - 노션 DB 컬럼명과 일치해야 함
    properties = {
        "이름": {"title": [{"text": {"content": f"📖 {base_name}"}}]},
        "원본 PDF": {"url": pdf_url if pdf_url else None},
        "강의 영상": {"url": media_url if media_url else None},
        "상태": {"select": {"name": "✅ 완료"}}
    }

    # 5. 페이지 본문(Children) 구성
    children = []
    
    # 미디어 임베드
    if media_url:
        embed_url = media_url.replace("/view?usp=drivesdk", "/preview")
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📺 강의 다시보기" if is_video else "🎧 강의 다시듣기"}}]}})
        children.append({"object": "block", "type": block_type, block_type: {"type": "external", "external": {"url": embed_url}}})

    # 요약 (split_by_newline=False를 추가하여 블록이 쪼개지지 않게 방어)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📌 강의 핵심 요약"}}]}})
    children.extend(create_rich_text_blocks(data["summary"], block_type="bulleted_list_item", split_by_newline=False))
    
    # 용어 (위와 동일)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📑 중요 용어 정리"}}]}})
    children.extend(create_rich_text_blocks(data["terms"], block_type="bulleted_list_item", split_by_newline=False))

    # 전체 스크립트 (기존처럼 문단마다 블록을 나누기 위해 옵션을 적지 않음)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📝 최종 교정 스크립트"}}]}})
    children.extend(create_rich_text_blocks(data["corrected_text"], block_type="paragraph", split_by_newline=True))

    try:
        # parent를 database_id로 설정하여 데이터베이스에 한 줄(Row)로 생성
        notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children
        )
        print(f"✅ [Notion] '{base_name}' 업로드 성공!")

        
        old_path = os.path.join(target_dir, f"{base_name}_result.json")
        new_path = os.path.join(target_dir, f"{base_name}_done.json")
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
    except Exception as e:
        print(f"❌ [Notion] 업로드 실패: {e}")