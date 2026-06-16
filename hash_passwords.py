# -*- coding: utf-8 -*-
"""backdata_performance.csv 비밀번호를 bcrypt 해시로 변환"""
from pathlib import Path

import bcrypt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "중간점검" / "backdata_performance.csv"


def is_bcrypt_hash(value: str) -> bool:
    return (value or "").startswith(("$2a$", "$2b$", "$2y$"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main():
    if not CSV_PATH.exists():
        raise SystemExit(f"파일 없음: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    updated = 0
    for idx, row in df.iterrows():
        pw = str(row.get("PW", "")).strip()
        if not pw or is_bcrypt_hash(pw):
            continue
        df.at[idx, "PW"] = hash_password(pw)
        updated += 1

    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"완료: {updated}개 비밀번호를 bcrypt 해시로 변환했습니다.")


if __name__ == "__main__":
    main()
