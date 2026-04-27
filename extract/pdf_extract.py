import fitz
import pytesseract
import cv2
import numpy as np

# Tesseract 설치 경로 (본인 환경에 맞게 수정)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_pdf(file_path):
    print(f"📄 PDF OCR 분석 시작.. (경로 : {file_path})")
    try:
        doc = fitz.open(file_path)
        full_text = ""
        
        # 엔진과 페이지 레이아웃 설정 (oem 1: LSTM 엔진, psm 6: 균일한 텍스트 블록 가정)
        custom_config = r'--oem 1 --psm 6'
        
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            
            if len(text) < 10:
                print(f"  🔍 {i+1} Page: 스캔본 감지, 고정밀 OCR을 실행합니다...")
                
                # 1. 해상도 극대화 (약 300~400 DPI 수준으로 뻥튀기)
                zoom = 4.0 
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # 2. PyMuPDF 픽스맵을 OpenCV에서 다룰 수 있는 Numpy 배열(이미지)로 변환
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                # 색상 채널이 4개(RGBA)인 경우 RGB로 변환, 혹은 그대로 BGR 처리
                if pix.n == 4:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # 3. [핵심 전처리] 그레이스케일(흑백 톤) 변환
                gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
                
                # 4. [핵심 전처리] 오츠의 이진화 (Otsu's Thresholding)
                # 배경과 글자의 대비를 극대화하여 글씨만 까맣고 선명하게 남깁니다.
                _, binary_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # 5. 전처리된 이미지를 Tesseract에 전달
                ocr_text = pytesseract.image_to_string(binary_img, lang='kor+eng', config=custom_config)
                text = ocr_text
            else:
                print(f"  ✅ {i+1} Page: 기본 텍스트 추출 완료.")
                
            full_text += f"\n--- {i+1} Page ---\n" + text
        
        doc.close()
        print(f"✨ PDF 분석 완료!")
        return full_text

    except Exception as e:
        print(f"❌ PDF 처리 오류: {e}")
        return None