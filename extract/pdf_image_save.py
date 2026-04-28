import os
from pdf2image import convert_from_path

def extract_pages_to_images(pdf_path, dpi=300):
    """
    PDF 파일을 읽어 지정된 양식(파일명_페이지번호.png)으로 변환하여 저장합니다.
    """
    # 파일 경로에서 확장자(.pdf)를 제외한 기본 이름만 추출
    # 예: "/Users/user/Downloads/0428_34.pdf" -> "0428_34"
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    if not os.path.exists(base_name + '_강의자료캡처'):
        os.makedirs(base_name + '_강의자료캡처')
        print(f"'{base_name + '_강의자료캡처'}' 폴더를 생성했습니다.")

    print(f"'{pdf_path}' 변환을 시작합니다...")
    
    try:
        pages = convert_from_path(pdf_path, dpi=dpi)
        
        for i, page in enumerate(pages):
            page_num = i + 1
            
            # 요청하신 저장 양식 적용: base_name_000.png
            file_name = f"{base_name}_{page_num:03d}.png"
            output_filepath = os.path.join(base_name + '_강의자료캡처', file_name)
            
            # 이미지 저장
            page.save(output_filepath, 'PNG')
            print(f"저장 완료: {output_filepath}")
            
        print("모든 페이지의 변환이 완료되었습니다!")
        return True

    except Exception as e:
        print(f"변환 중 오류가 발생했습니다: {e}")
        return False