# -*- coding: utf-8 -*-
"""
동국홀딩스 2026 평가시스템 - 중간점검 모듈
실적등록(팀원), 실적조회(팀장), 관리자 화면
"""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))
BACKDATA_CSV = BASE_DIR / "중간점검" / "backdata_performance.csv"
PROJECT_CSV = BASE_DIR / "중간점검" / "project_nm.csv"
PERFORMANCE_JSON = DATA_DIR / "중간점검" / "performance_data.json"

MAX_ITEMS = 10
ADMIN_USER_ID = "11210110"

performance_bp = Blueprint(
    "performance",
    __name__,
    url_prefix="/midterm",
)

_users_cache = None
_projects_cache = None


def _normalize_team(team: str) -> str:
    """backdata 팀명을 project_nm 팀명으로 변환"""
    team = (team or "").strip()
    if team.startswith("전략실 "):
        return team.replace("전략실 ", "", 1)
    return team


def load_users():
    """backdata_performance.csv에서 사용자 목록 로드"""
    global _users_cache
    if _users_cache is not None:
        return _users_cache
    if not BACKDATA_CSV.exists():
        _users_cache = []
        return _users_cache
    try:
        df = pd.read_csv(BACKDATA_CSV, dtype=str).fillna("")
        users = []
        for _, row in df.iterrows():
            users.append({
                "id": str(row.get("ID", "")).strip(),
                "pw": str(row.get("PW", "")).strip(),
                "name": str(row.get("name", "")).strip(),
                "team": str(row.get("team", "")).strip(),
                "grade": str(row.get("grade", "")).strip(),
                "position": str(row.get("position", "")).strip(),
            })
        _users_cache = users
        return users
    except Exception as e:
        print(f"backdata_performance.csv 로드 실패: {e}")
        _users_cache = []
        return _users_cache


def load_projects():
    """project_nm.csv에서 팀별 과제명 로드"""
    global _projects_cache
    if _projects_cache is not None:
        return _projects_cache
    if not PROJECT_CSV.exists():
        _projects_cache = {}
        return _projects_cache
    try:
        df = pd.read_csv(PROJECT_CSV, dtype=str).fillna("")
        result = {}
        for _, row in df.iterrows():
            team = str(row.get("team", "")).strip()
            pj_nm = str(row.get("pj_nm", "")).strip()
            if not team or not pj_nm:
                continue
            result.setdefault(team, []).append(pj_nm)
        _projects_cache = result
        return result
    except Exception as e:
        print(f"project_nm.csv 로드 실패: {e}")
        _projects_cache = {}
        return _projects_cache


def get_user_by_credentials(user_id: str, password: str):
    """ID/PW로 사용자 조회"""
    user_id = (user_id or "").strip()
    password = (password or "").strip()
    for user in load_users():
        if user["id"] == user_id and user["pw"] == password:
            return user
    return None


def get_team_projects(team: str):
    """팀별 과제명 목록"""
    normalized = _normalize_team(team)
    return load_projects().get(normalized, [])


def get_team_members(team: str, position=None):
    """같은 팀 구성원 목록"""
    members = []
    for user in load_users():
        if user["team"] != team:
            continue
        if position and user["position"] != position:
            continue
        members.append(user)
    return members


def load_performance_data():
    """저장된 실적 데이터 로드"""
    if not PERFORMANCE_JSON.exists():
        return {}
    try:
        with open(PERFORMANCE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_performance_data(data: dict):
    """실적 데이터 저장"""
    PERFORMANCE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(PERFORMANCE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_performance(user_id: str):
    return load_performance_data().get(user_id)


def _require_login():
    user = session.get("performance_user")
    if not user:
        return None
    return user


def _require_mode(*modes):
    user = _require_login()
    if not user or user.get("mode") not in modes:
        return None
    return user


def _require_admin():
    if not session.get("performance_admin"):
        return False
    return True


@performance_bp.route("/")
def login_page():
    """로그인 화면"""
    session.pop("performance_user", None)
    session.pop("performance_admin", None)
    return render_template("performance/login.html", error="")


@performance_bp.route("/login", methods=["POST"])
def login():
    """로그인 처리"""
    mode = (request.form.get("mode") or "").strip()
    user_id = (request.form.get("user_id") or "").strip()
    password = (request.form.get("password") or "").strip()

    if mode not in ("register", "inquiry", "admin"):
        return render_template("performance/login.html", error="접속 유형을 선택해 주세요.")

    user = get_user_by_credentials(user_id, password)
    if mode == "admin":
        if not user:
            return render_template("performance/login.html", error="ID 또는 비밀번호가 올바르지 않습니다.")
        if user["id"] != ADMIN_USER_ID:
            return render_template("performance/login.html", error="관리자 화면 접근 권한이 없습니다.")
        session["performance_admin"] = True
        session.pop("performance_user", None)
        return redirect(url_for("performance.admin_page"))

    if not user:
        return render_template("performance/login.html", error="ID 또는 비밀번호가 올바르지 않습니다.")

    if mode == "register" and user["position"] != "팀원":
        return render_template("performance/login.html", error="실적등록은 팀원만 이용할 수 있습니다.")
    if mode == "inquiry" and user["position"] != "팀장":
        return render_template("performance/login.html", error="실적조회는 팀장만 이용할 수 있습니다.")

    session.pop("performance_admin", None)
    session["performance_user"] = {**user, "mode": mode}

    if mode == "register":
        return redirect(url_for("performance.register_page"))
    return redirect(url_for("performance.inquiry_page"))


@performance_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("performance_user", None)
    session.pop("performance_admin", None)
    return redirect(url_for("performance.login_page"))


@performance_bp.route("/register")
def register_page():
    """실적등록 화면 (팀원)"""
    user = _require_mode("register")
    if not user:
        return redirect(url_for("performance.login_page"))

    perf = get_user_performance(user["id"]) or {}
    status = perf.get("status", "none")
    projects = get_team_projects(user["team"])

    return render_template(
        "performance/register.html",
        user=user,
        projects=projects,
        status=status,
        max_items=MAX_ITEMS,
    )


@performance_bp.route("/inquiry")
def inquiry_page():
    """실적조회 화면 (팀장)"""
    user = _require_mode("inquiry")
    if not user:
        return redirect(url_for("performance.login_page"))

    members = get_team_members(user["team"], position="팀원")
    all_data = load_performance_data()

    member_rows = []
    for m in members:
        perf = all_data.get(m["id"], {})
        interview = perf.get("interview") or {}
        member_rows.append({
            "id": m["id"],
            "name": m["name"],
            "grade": m["grade"],
            "status": perf.get("status", "none"),
            "interview_done": bool(interview.get("done")),
            "interview_at": interview.get("checked_at", ""),
        })

    return render_template(
        "performance/inquiry.html",
        user=user,
        members=member_rows,
    )


@performance_bp.route("/admin")
def admin_page():
    """관리자 화면"""
    if not _require_admin():
        return redirect(url_for("performance.login_page"))

    all_data = load_performance_data()
    users = load_users()
    rows = []
    for u in users:
        if u["position"] != "팀원":
            continue
        perf = all_data.get(u["id"], {})
        interview = perf.get("interview") or {}
        rows.append({
            "id": u["id"],
            "name": u["name"],
            "team": u["team"],
            "grade": u["grade"],
            "status": perf.get("status", "none"),
            "updated_at": perf.get("updated_at", ""),
            "item_count": len(perf.get("items", [])),
            "interview_done": bool(interview.get("done")),
            "interview_at": interview.get("checked_at", ""),
            "interview_leader": interview.get("leader_name", ""),
        })

    return render_template("performance/admin.html", rows=rows)


@performance_bp.route("/api/my-performance")
def api_my_performance():
    """본인 실적 조회 (등록 화면용)"""
    user = _require_mode("register")
    if not user:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    perf = get_user_performance(user["id"])
    if not perf:
        return jsonify({"success": True, "status": "none", "items": []})

    return jsonify({
        "success": True,
        "status": perf.get("status", "draft"),
        "items": perf.get("items", []),
    })


@performance_bp.route("/api/save", methods=["POST"])
def api_save():
    """실적 임시저장"""
    user = _require_mode("register")
    if not user:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json() or {}
    items = data.get("items", [])
    if not isinstance(items, list):
        return jsonify({"success": False, "message": "잘못된 데이터 형식입니다."}), 400
    if len(items) > MAX_ITEMS:
        return jsonify({"success": False, "message": f"과제는 최대 {MAX_ITEMS}개까지 등록할 수 있습니다."}), 400

    all_data = load_performance_data()
    existing = all_data.get(user["id"], {})
    if existing.get("status") == "submitted":
        return jsonify({"success": False, "message": "이미 최종 제출되어 수정할 수 없습니다."}), 400

    normalized_items = []
    for item in items:
        project_name = (item.get("project_name") or "").strip()
        performance_text = (item.get("performance") or "").strip()
        is_custom = bool(item.get("is_custom"))
        if not project_name:
            continue
        normalized_items.append({
            "project_name": project_name,
            "is_custom": is_custom,
            "performance": performance_text,
        })

    all_data[user["id"]] = {
        "user_id": user["id"],
        "name": user["name"],
        "team": user["team"],
        "status": "draft",
        "items": normalized_items,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_performance_data(all_data)
    return jsonify({"success": True, "message": "임시저장되었습니다."})


@performance_bp.route("/api/submit", methods=["POST"])
def api_submit():
    """실적 최종 제출"""
    user = _require_mode("register")
    if not user:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json() or {}
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        return jsonify({"success": False, "message": "제출할 과제가 없습니다."}), 400
    if len(items) > MAX_ITEMS:
        return jsonify({"success": False, "message": f"과제는 최대 {MAX_ITEMS}개까지 등록할 수 있습니다."}), 400

    all_data = load_performance_data()
    existing = all_data.get(user["id"], {})
    if existing.get("status") == "submitted":
        return jsonify({"success": False, "message": "이미 최종 제출되었습니다."}), 400

    normalized_items = []
    for item in items:
        project_name = (item.get("project_name") or "").strip()
        performance_text = (item.get("performance") or "").strip()
        is_custom = bool(item.get("is_custom"))
        if not project_name:
            return jsonify({"success": False, "message": "과제명을 입력해 주세요."}), 400
        if not performance_text:
            return jsonify({"success": False, "message": "중간실적을 입력해 주세요."}), 400
        normalized_items.append({
            "project_name": project_name,
            "is_custom": is_custom,
            "performance": performance_text,
        })

    all_data[user["id"]] = {
        "user_id": user["id"],
        "name": user["name"],
        "team": user["team"],
        "status": "submitted",
        "items": normalized_items,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_performance_data(all_data)
    return jsonify({"success": True, "message": "최종 제출되었습니다. 이후 수정할 수 없습니다."})


@performance_bp.route("/api/member/<member_id>")
def api_member_performance(member_id):
    """팀원 실적 조회 (팀장/관리자)"""
    user = _require_mode("inquiry")
    is_admin = _require_admin()
    if not user and not is_admin:
        return jsonify({"success": False, "message": "권한이 없습니다."}), 401

    target = None
    for u in load_users():
        if u["id"] == member_id:
            target = u
            break
    if not target:
        return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."}), 404

    if user and not is_admin:
        if target["team"] != user["team"]:
            return jsonify({"success": False, "message": "같은 팀 팀원만 조회할 수 있습니다."}), 403
        if target["position"] != "팀원":
            return jsonify({"success": False, "message": "팀원만 조회할 수 있습니다."}), 403

    perf = get_user_performance(member_id)
    if not perf or perf.get("status") != "submitted":
        return jsonify({"success": False, "message": "최종 제출된 실적이 없습니다."}), 404

    return jsonify({
        "success": True,
        "name": target["name"],
        "team": target["team"],
        "grade": target["grade"],
        "status": perf.get("status"),
        "items": perf.get("items", []),
        "submitted_at": perf.get("submitted_at", ""),
        "interview_done": bool((perf.get("interview") or {}).get("done")),
    })


@performance_bp.route("/api/interview/<member_id>", methods=["POST"])
def api_save_interview(member_id):
    """팀장용 면담 여부 저장"""
    user = _require_mode("inquiry")
    if not user:
        return jsonify({"success": False, "message": "권한이 없습니다."}), 401

    target = None
    for u in load_users():
        if u["id"] == member_id:
            target = u
            break
    if not target:
        return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."}), 404

    if target["team"] != user["team"]:
        return jsonify({"success": False, "message": "같은 팀 팀원만 관리할 수 있습니다."}), 403
    if target["position"] != "팀원":
        return jsonify({"success": False, "message": "팀원만 관리할 수 있습니다."}), 403

    data = request.get_json() or {}
    done = bool(data.get("done"))

    all_data = load_performance_data()
    record = dict(all_data.get(member_id, {}))
    record.setdefault("user_id", member_id)
    record.setdefault("name", target["name"])
    record.setdefault("team", target["team"])

    if done:
        record["interview"] = {
            "done": True,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "leader_id": user["id"],
            "leader_name": user["name"],
        }
    else:
        record["interview"] = {"done": False}

    all_data[member_id] = record
    save_performance_data(all_data)
    return jsonify({
        "success": True,
        "message": "면담 여부가 저장되었습니다.",
        "interview_done": done,
        "interview_at": record["interview"].get("checked_at", ""),
    })


@performance_bp.route("/api/admin/member/<member_id>")
def api_admin_member_performance(member_id):
    """관리자용 팀원 실적 조회 (임시저장 포함)"""
    if not _require_admin():
        return jsonify({"success": False, "message": "권한이 없습니다."}), 401

    target = None
    for u in load_users():
        if u["id"] == member_id:
            target = u
            break
    if not target:
        return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."}), 404

    perf = get_user_performance(member_id)
    if not perf:
        return jsonify({"success": False, "message": "작성된 실적이 없습니다."}), 404

    interview = perf.get("interview") or {}
    return jsonify({
        "success": True,
        "name": target["name"],
        "team": target["team"],
        "grade": target["grade"],
        "status": perf.get("status"),
        "items": perf.get("items", []),
        "updated_at": perf.get("updated_at", ""),
        "submitted_at": perf.get("submitted_at", ""),
        "interview_done": bool(interview.get("done")),
        "interview_at": interview.get("checked_at", ""),
        "interview_leader": interview.get("leader_name", ""),
    })


@performance_bp.route("/api/admin/reset/<member_id>", methods=["POST"])
def api_admin_reset(member_id):
    """관리자용 개인 실적 초기화"""
    if not _require_admin():
        return jsonify({"success": False, "message": "권한이 없습니다."}), 401

    all_data = load_performance_data()
    if member_id not in all_data:
        return jsonify({"success": False, "message": "초기화할 데이터가 없습니다."}), 404

    del all_data[member_id]
    save_performance_data(all_data)
    return jsonify({"success": True, "message": "해당 팀원의 실적이 초기화되었습니다."})
