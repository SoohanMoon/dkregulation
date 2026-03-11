# -*- coding: utf-8 -*-
"""
동국홀딩스 2026년 팀별 목표등록 시스템 - Flask 웹 앱
"""
import json
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for

from objectmanagement import (
    TEAMS,
    TEAMMATE_XLSX,
    YEAROBJECT_XLSX,
    GOALS_JSON,
    EXCEL_TEAM_TO_ID,
)

app = Flask(__name__)
app.secret_key = "dgh_2026_admin_secret"
ID_TO_TEAM_NAME = {t["id"]: t["name"] for t in TEAMS}


def load_teammates():
    """teammate.xlsx에서 팀별 팀원 로드"""
    if not TEAMMATE_XLSX.exists():
        return {}
    try:
        import pandas as pd
        df = pd.read_excel(TEAMMATE_XLSX)
        df = df.astype(str)
        result = {}
        for _, row in df.iterrows():
            team_name = row.get("team", "").strip()
            tid = EXCEL_TEAM_TO_ID.get(team_name)
            if tid is None:
                tid = team_name  # 매핑 없으면 팀명 그대로
            if tid not in result:
                result[tid] = []
            result[tid].append({
                "name": row.get("name", "").strip(),
                "jikwi": row.get("jikwi", "").strip(),
            })
        return result
    except Exception as e:
        print(f"teammate.xlsx 로드 실패: {e}")
        return {}


def load_goals():
    """저장된 목표 목록 로드"""
    if not GOALS_JSON.exists():
        return []
    try:
        with open(GOALS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_goals(goals):
    """목표 목록 저장"""
    with open(GOALS_JSON, "w", encoding="utf-8") as f:
        json.dump(goals, f, ensure_ascii=False, indent=2)


# 앱 시작 시 팀원 캐시
_teammates_cache = None


def get_teammates():
    global _teammates_cache
    if _teammates_cache is None:
        _teammates_cache = load_teammates()
    return _teammates_cache


def persons_to_text(persons):
    """담당자 리스트를 표시용 문자열로 변환"""
    if not isinstance(persons, list):
        return ""
    result = []
    for p in persons:
        if isinstance(p, dict):
            name = (p.get("name") or "").strip()
            jikwi = (p.get("jikwi") or "").strip()
            if name and jikwi:
                result.append(f"{name}({jikwi})")
            elif name:
                result.append(name)
    return ", ".join(result)


@app.route("/")
def index():
    """메인: 팀별 버튼"""
    return render_template("index.html", teams=TEAMS)


@app.route("/team/<team_id>")
def team_goal_page(team_id):
    """팀별 목표 등록 페이지"""
    team_name = ID_TO_TEAM_NAME.get(team_id) or team_id
    return render_template("goal_register.html", team_id=team_id, team_name=team_name)


@app.route("/admin")
def admin_page():
    """관리자 화면"""
    if not session.get("is_admin_authed"):
        return redirect(url_for("admin_login_page"))
    return render_template("admin.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login_page():
    """관리자 로그인 화면"""
    if request.method == "POST":
        password = (request.form.get("password") or "").strip()
        if password == "3333":
            session["is_admin_authed"] = True
            return redirect(url_for("admin_page"))
        return render_template("admin_login.html", error="비밀번호가 올바르지 않습니다.")
    return render_template("admin_login.html", error="")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin_authed", None)
    return redirect(url_for("index"))


@app.route("/api/teams")
def api_teams():
    """팀 목록 API"""
    return jsonify(TEAMS)


@app.route("/api/team/<team_id>/members")
def api_team_members(team_id):
    """팀별 팀원 목록 API (담당자 팝업용)"""
    members = get_teammates().get(team_id, [])
    return jsonify(members)


@app.route("/api/team/<team_id>/goals")
def api_team_goals(team_id):
    """팀별 저장된 목표 목록 API (다시 들어왔을 때 표시용)"""
    all_goals = load_goals()
    team_goals = [g for g in all_goals if g.get("team_id") == team_id]
    return jsonify(team_goals)


@app.route("/api/team/<team_id>/year-objects")
def api_team_year_objects(team_id):
    """팀별 연두보고 참고 과제 API (yearobject.xlsx 시트 기반)"""
    team_name = ID_TO_TEAM_NAME.get(team_id)
    if not team_name:
        return jsonify({"success": False, "message": "유효하지 않은 팀입니다."}), 400
    if not YEAROBJECT_XLSX.exists():
        return jsonify({"success": False, "message": "참고 파일이 없습니다.", "rows": []}), 404
    try:
        import pandas as pd

        df = pd.read_excel(YEAROBJECT_XLSX, sheet_name=team_name)
        df = df.fillna("")
        rows = []
        for _, row in df.iterrows():
            row_data = {
                "대분류": str(row.get("대분류", "")).strip(),
                "중분류": str(row.get("중분류", "")).strip(),
            }
            # 일부 시트(예: 윤리경영팀)는 소분류 컬럼이 없을 수 있음
            if "소분류" in df.columns:
                row_data["소분류"] = str(row.get("소분류", "")).strip()
            rows.append(row_data)
        return jsonify({"success": True, "team_name": team_name, "rows": rows})
    except Exception as e:
        return jsonify({"success": False, "message": f"참고 과제 로드 실패: {e}", "rows": []}), 500


@app.route("/api/goals", methods=["POST"])
def api_save_goals():
    """목표 저장 API: 해당 팀 목표를 전부 이 내용으로 덮어씀 (다시 들어왔을 때 유지)"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "데이터가 없습니다."}), 400
    team_id = data.get("team_id")
    team_name = data.get("team_name")
    items = data.get("goals", [])  # [{ goal_type, task_name, task_description, persons }, ...]
    if not team_id or not team_name:
        return jsonify({"success": False, "message": "팀 정보가 없습니다."}), 400
    goals = load_goals()
    goals = [g for g in goals if g.get("team_id") != team_id]
    saved = 0
    for item in items:
        goal_type = item.get("goal_type")
        task_name = (item.get("task_name") or "").strip()
        if not goal_type or not task_name:
            continue
        goals.append({
            "team_id": team_id,
            "team_name": team_name,
            "goal_type": goal_type,
            "task_name": task_name,
            "task_description": (item.get("task_description") or "").strip(),
            "persons": item.get("persons") or [],
        })
        saved += 1
    save_goals(goals)
    return jsonify({"success": True, "message": f"{saved}건 저장되었습니다."})


@app.route("/api/admin/goals")
def api_admin_goals():
    """관리자용 전체 목표 목록 API"""
    if not session.get("is_admin_authed"):
        return jsonify({"success": False, "message": "인증이 필요합니다."}), 401
    goals = load_goals()
    normalized = []
    for g in goals:
        normalized.append({
            "team_name": g.get("team_name", ""),
            "goal_type": g.get("goal_type", ""),
            "task_name": g.get("task_name", ""),
            "task_description": g.get("task_description", ""),
            "persons": g.get("persons", []),
            "persons_text": persons_to_text(g.get("persons", [])),
        })
    return jsonify({"success": True, "rows": normalized})


@app.route("/api/admin/goals/download")
def api_admin_goals_download():
    """관리자용 목표 목록 엑셀 다운로드"""
    if not session.get("is_admin_authed"):
        return jsonify({"success": False, "message": "인증이 필요합니다."}), 401
    import pandas as pd

    goals = load_goals()
    rows = []
    for i, g in enumerate(goals, start=1):
        rows.append({
            "번호": i,
            "팀": g.get("team_name", ""),
            "목표구분": g.get("goal_type", ""),
            "과제명": g.get("task_name", ""),
            "과제설명": g.get("task_description", ""),
            "담당자": persons_to_text(g.get("persons", [])),
        })

    df = pd.DataFrame(rows, columns=["번호", "팀", "목표구분", "과제명", "과제설명", "담당자"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="팀목표")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="팀별_목표_등록현황.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/admin/goals/reset", methods=["POST"])
def api_admin_goals_reset():
    """관리자용 전체 목표 데이터 초기화"""
    if not session.get("is_admin_authed"):
        return jsonify({"success": False, "message": "인증이 필요합니다."}), 401
    save_goals([])
    return jsonify({"success": True, "message": "전체 목표 데이터가 초기화되었습니다."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
