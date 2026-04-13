import os
import re
import json
import zipfile
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGULATION_DIR = os.path.join(BASE_DIR, "company-regulation")
OUTPUT_FILE = os.path.join(BASE_DIR, "search_index.json")

def sort_key(filename):
    """파일명의 숫자 접두어를 기준으로 정렬하기 위한 함수"""
    match = re.match(r'^(\d+)', filename)
    if match:
        return int(match.group(1))
    return float('inf')

def extract_text_from_docx(file_path):
    """DOCX 파일 내의 텍스트를 파싱하여 문자열로 반환 (내장 zipfile 지원)"""
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            # 모든 텍스트 노드의 내용을 합침
            text = ''.join(node.text for node in tree.iter() if node.text)
            return text
    except Exception as e:
        print(f"[{file_path}] DOCX 파싱 오류: {e}")
        return ""

def build_index():
    print("사규 파일을 읽어 검색 인덱스를 빌드합니다...")
    
    if not os.path.exists(REGULATION_DIR):
        print(f"[{REGULATION_DIR}] 폴더를 찾을 수 없습니다.")
        return

    files = [f for f in os.listdir(REGULATION_DIR) if f.endswith('.docx')]
    files = sorted(files, key=sort_key)
    
    index_data = {
        "files": [],
        "content_map": {}
    }
    
    for filename in files:
        index_data["files"].append(filename)
        file_path = os.path.join(REGULATION_DIR, filename)
        content = extract_text_from_docx(file_path)
        index_data["content_map"][filename] = content
        print(f" - 처리 완료: {filename} ({len(content)} 글자)")
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False)
        
    print(f"\n빌드 완료! '{OUTPUT_FILE}'가 생성되었습니다.")
    print("이제 파이썬 서버 없이 GitHub Pages 등에서 정적으로 서비스가 가능합니다.")

if __name__ == "__main__":
    build_index()
