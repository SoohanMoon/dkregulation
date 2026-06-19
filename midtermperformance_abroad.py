# -*- coding: utf-8 -*-
"""
동국홀딩스 2026 평가시스템 - 해외법인 중간점검 모듈
실적등록(임직원), 실적조회(법인장), 관리자 화면
"""
import json
import os
from datetime import datetime
from pathlib import Path

import bcrypt
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
ABROAD_DIR = BASE_DIR / "중간점검(해외)"
BACKDATA_CSV = ABROAD_DIR / "backdata_midtermperformance_abroad - 시트1.csv"
DOMESTIC_BACKDATA_CSV = BASE_DIR / "중간점검" / "backdata_performance.csv"
PERFORMANCE_JSON = DATA_DIR / "중간점검(해외)" / "performance_data_abroad.json"

MAX_ITEMS = 10
ADMIN_USER_ID = "11210110"
POSITION_LEADER = "법인장"

performance_abroad_bp = Blueprint(
    "performance_abroad",
    __name__,
    url_prefix="/midterm/abroad",
    template_folder="templates",
)

_users_cache = None
_users_cache_mtime = None


def _is_bcrypt_hash(value: str) -> bool:
    return (value or "").startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(plain: str, stored: str) -> bool:
    """평문 비밀번호와 저장값(bcrypt 해시) 비교"""
    if not plain or not stored:
        return False
    if _is_bcrypt_hash(stored):
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    return plain == stored


def _user_for_session(user: dict) -> dict:
    """세션/API용 사용자 정보 (비밀번호 해시 제외)"""
    return {k: v for k, v in user.items() if k != "pw_hash"}


def _is_leader(position: str) -> bool:
    return (position or "").strip() == POSITION_LEADER


def _is_member(position: str) -> bool:
    return not _is_leader(position)


def _load_users_from_csv(csv_path: Path):
    if not csv_path.exists():
        return []
    try:
        df = pd.read_csv(csv_path, dtype=str).fillna("")
        users = []
        for _, row in df.iterrows():
            users.append({
                "id": str(row.get("ID", "")).strip(),
                "pw_hash": str(row.get("PW", "")).strip(),
                "name": str(row.get("name", "")).strip(),
                "team": str(row.get("team", "")).strip(),
                "grade": str(row.get("grade", "")).strip(),
                "position": str(row.get("position", "")).strip(),
            })
        return users
    except Exception as e:
        print(f"{csv_path.name} 로드 실패: {e}")
        return []


def _is_register_user(position: str) -> bool:
    return _is_member(position) and (position or "").strip() != "관리자"


def load_users():
    """해외법인 backdata CSV에서 사용자 목록 로드"""
    global _users_cache, _users_cache_mtime
    mtime = BACKDATA_CSV.stat().st_mtime if BACKDATA_CSV.exists() else None
    if _users_cache is not None and _users_cache_mtime == mtime:
        return _users_cache
    _users_cache = _load_users_from_csv(BACKDATA_CSV)
    _users_cache_mtime = mtime
    return _users_cache


def get_user_by_credentials(user_id: str, password: str):
    """ID/PW로 사용자 조회"""
    user_id = (user_id or "").strip()
    password = (password or "").strip()
    for user in load_users():
        if user["id"] == user_id and verify_password(password, user["pw_hash"]):
            return _user_for_session(user)
    return None


def get_admin_user(user_id: str, password: str):
    """관리자 로그인 (해외 backdata 우선, 본사 backdata 폴백)"""
    user_id = (user_id or "").strip()
    password = (password or "").strip()
    if user_id != ADMIN_USER_ID:
        return None

    user = get_user_by_credentials(user_id, password)
    if user:
        return user

    for user in _load_users_from_csv(DOMESTIC_BACKDATA_CSV):
        if user["id"] == user_id and verify_password(password, user["pw_hash"]):
            return _user_for_session(user)
    return None


def get_team_members(team: str, position=None):
    """같은 법인 구성원 목록"""
    members = []
    for user in load_users():
        if user["team"] != team:
            continue
        if position == "member" and not _is_register_user(user["position"]):
            continue
        if position == POSITION_LEADER and not _is_leader(user["position"]):
            continue
        members.append(_user_for_session(user))
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
    user = session.get("performance_abroad_user")
    if not user:
        return None
    return user


def _require_mode(*modes):
    user = _require_login()
    if not user or user.get("mode") not in modes:
        return None
    return user


def _require_admin():
    if not session.get("performance_abroad_admin"):
        return False
    return True


@performance_abroad_bp.route("/")
def login_page():
    """로그인 화면"""
    session.pop("performance_abroad_user", None)
    session.pop("performance_abroad_admin", None)
    return render_template("performance_abroad/login.html", error="")


@performance_abroad_bp.route("/login", methods=["POST"])
def login():
    """로그인 처리"""
    mode = (request.form.get("mode") or "").strip()
    user_id = (request.form.get("user_id") or "").strip()
    password = (request.form.get("password") or "").strip()

    if mode not in ("register", "inquiry", "admin"):
        return render_template("performance_abroad/login.html", error="접속 유형을 선택해 주세요.")

    if mode == "admin":
        user = get_admin_user(user_id, password)
        if not user:
            return render_template("performance_abroad/login.html", error="ID 또는 비밀번호가 올바르지 않습니다.")
        session["performance_abroad_admin"] = True
        session.pop("performance_abroad_user", None)
        return redirect(url_for("performance_abroad.admin_page"))

    user = get_user_by_credentials(user_id, password)
    if not user:
        return render_template("performance_abroad/login.html", error="ID 또는 비밀번호가 올바르지 않습니다.")

    if mode == "register" and not _is_register_user(user["position"]):
        return render_template("performance_abroad/login.html", error="실적등록은 법인장·관리자를 제외한 임직원만 이용할 수 있습니다.")
    if mode == "inquiry" and not _is_leader(user["position"]):
        return render_template("performance_abroad/login.html", error="실적조회는 법인장만 이용할 수 있습니다.")

    session.pop("performance_abroad_admin", None)
    session["performance_abroad_user"] = {**user, "mode": mode}

    if mode == "register":
        return redirect(url_for("performance_abroad.register_page"))
    return redirect(url_for("performance_abroad.inquiry_page"))


@performance_abroad_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("performance_abroad_user", None)
    session.pop("performance_abroad_admin", None)
    return redirect(url_for("performance_abroad.login_page"))


@performance_abroad_bp.route("/register")
def register_page():
    """실적등록 화면 (임직원)"""
    user = _require_mode("register")
    if not user:
        return redirect(url_for("performance_abroad.login_page"))

    perf = get_user_performance(user["id"]) or {}
    status = perf.get("status", "none")

    return render_template(
        "performance_abroad/register.html",
        user=user,
        status=status,
        max_items=MAX_ITEMS,
    )


@performance_abroad_bp.route("/inquiry")
def inquiry_page():
    """실적조회 화면 (법인장)"""
    user = _require_mode("inquiry")
    if not user:
        return redirect(url_for("performance_abroad.login_page"))

    members = get_team_members(user["team"], position="member")
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
        "performance_abroad/inquiry.html",
        user=user,
        members=member_rows,
    )


@performance_abroad_bp.route("/admin")
def admin_page():
    """관리자 화면"""
    if not _require_admin():
        return redirect(url_for("performance_abroad.login_page"))

    all_data = load_performance_data()
    users = load_users()
    rows = []
    for u in users:
        if u["id"] == ADMIN_USER_ID or not _is_register_user(u["position"]):
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

    return render_template("performance_abroad/admin.html", rows=rows)


@performance_abroad_bp.route("/api/my-performance")
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


@performance_abroad_bp.route("/api/save", methods=["POST"])
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


@performance_abroad_bp.route("/api/submit", methods=["POST"])
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


@performance_abroad_bp.route("/api/member/<member_id>")
def api_member_performance(member_id):
    """임직원 실적 조회 (법인장/관리자)"""
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
            return jsonify({"success": False, "message": "같은 법인 임직원만 조회할 수 있습니다."}), 403
        if not _is_register_user(target["position"]):
            return jsonify({"success": False, "message": "임직원만 조회할 수 있습니다."}), 403

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


@performance_abroad_bp.route("/api/interview/<member_id>", methods=["POST"])
def api_save_interview(member_id):
    """법인장용 면담 여부 저장"""
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
        return jsonify({"success": False, "message": "같은 법인 임직원만 관리할 수 있습니다."}), 403
    if not _is_register_user(target["position"]):
        return jsonify({"success": False, "message": "임직원만 관리할 수 있습니다."}), 403

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


@performance_abroad_bp.route("/api/admin/member/<member_id>")
def api_admin_member_performance(member_id):
    """관리자용 임직원 실적 조회 (임시저장 포함)"""
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


@performance_abroad_bp.route("/api/admin/reset/<member_id>", methods=["POST"])
def api_admin_reset(member_id):
    """관리자용 개인 실적 초기화"""
    if not _require_admin():
        return jsonify({"success": False, "message": "권한이 없습니다."}), 401

    all_data = load_performance_data()
    if member_id not in all_data:
        return jsonify({"success": False, "message": "초기화할 데이터가 없습니다."}), 404

    del all_data[member_id]
    save_performance_data(all_data)
    return jsonify({"success": True, "message": "해당 임직원의 실적이 초기화되었습니다."})
