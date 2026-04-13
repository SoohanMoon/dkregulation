import os
import re
import zipfile
import xml.etree.ElementTree as ET
from flask import Flask, render_template, jsonify, send_file, request

app = Flask(__name__)
# 현재 파일 위치(Pdata)를 기준으로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGULATION_DIR = os.path.join(BASE_DIR, "company-regulation")

def sort_key(filename):
    """파일명의 숫자 접두어를 기준으로 정렬하기 위한 함수"""
    match = re.match(r'^(\d+)', filename)
    if match:
        return int(match.group(1))
    return float('inf')

def extract_text_from_docx(file_path):
    """DOCX 파일 내의 텍스트를 파싱하여 문자열로 반환 (별도 패키지 없이 내장 zipfile 사용)"""
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

@app.route("/")
def index():
    """메인 HTML 템플릿 렌더링"""
    return render_template("regulation.html")

@app.route("/api/list")
def list_regulations():
    """사규 파일 목록 반환 API"""
    if not os.path.exists(REGULATION_DIR):
        return jsonify({"error": "사규 폴더를 찾을 수 없습니다."}), 404
    
    files = [f for f in os.listdir(REGULATION_DIR) if f.endswith('.docx') or f.endswith('.pdf')]
    files = sorted(files, key=sort_key)
    return jsonify({"files": files})

@app.route("/api/view/<path:filename>")
def view_file_route(filename):
    """사규 파일 원본 스트림 반환 API (브라우저에서 렌더링용)"""
    file_path = os.path.join(REGULATION_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=False)
    return "File not found", 404

@app.route("/api/search")
def search_regulations():
    """사규 전체 내용 풀텍스트 검색 API"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": []})
        
    if not os.path.exists(REGULATION_DIR):
        return jsonify({"error": "사규 폴더를 찾을 수 없습니다."}), 404
        
    files = [f for f in os.listdir(REGULATION_DIR) if f.endswith('.docx')]
    files = sorted(files, key=sort_key)
    
    results = []
    query_lower = query.lower()
    
    for filename in files:
        file_path = os.path.join(REGULATION_DIR, filename)
        content = extract_text_from_docx(file_path)
        if not content:
            continue
            
        content_lower = content.lower()
        matches = []
        start_idx = 0
        
        while True:
            idx = content_lower.find(query_lower, start_idx)
            if idx == -1 or len(matches) >= 3: # 문서당 최대 3개의 매칭 결과만 포함
                break
                
            # 앞뒤 40글자 정도의 문맥 생성
            snippet_start = max(0, idx - 40)
            snippet_end = min(len(content), idx + len(query) + 40)
            
            snippet = content[snippet_start:snippet_end]
            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(content):
                snippet = snippet + "..."
                
            matches.append(snippet)
            start_idx = idx + len(query)
            
        if matches:
            results.append({
                "filename": filename,
                "matches": matches
            })
            
    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
