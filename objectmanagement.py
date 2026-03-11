# -*- coding: utf-8 -*-
"""
동국홀딩스 2026 팀별 목표등록 - 목표/팀 데이터 관리
팀 목록, Excel 경로, 목표 저장 경로 정의.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEAMMATE_XLSX = BASE_DIR / "teammate(2).xlsx"
YEAROBJECT_XLSX = BASE_DIR / "yearobject.xlsx"
GOALS_JSON = BASE_DIR / "goals.json"

# 팀 목록: id(URL/API용), name(화면 표시명)
TEAMS = [
    {"id": "strategy", "name": "전략팀"},
    {"id": "finance", "name": "재경팀"},
    {"id": "communication", "name": "커뮤니케이션팀"},
    {"id": "ethics", "name": "윤리경영팀"},
    {"id": "hr", "name": "인사기획팀"},
    {"id": "secretary", "name": "비서팀"},
]

EXCEL_TEAM_TO_ID = {
    "전략팀": "strategy",
    "재경팀": "finance",
    "커뮤니케이션팀": "communication",
    "윤리경영팀": "ethics",
    "인사기획팀": "hr",
    "비서팀": "secretary",
}
