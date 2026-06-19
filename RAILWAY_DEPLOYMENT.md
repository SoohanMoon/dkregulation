# Railway 배포 가이드 — 동국홀딩스 2026 평가시스템

목표등록 + **국내 중간점검** 시스템을 Railway에 배포하는 방법입니다.

> 해외법인 중간점검은 별도 저장소 [`SoohanMoon/dk-midterm-abroad`](https://github.com/SoohanMoon/dk-midterm-abroad)로 배포합니다.

## 사전 준비

- [Railway](https://railway.app) 계정 (GitHub 로그인 권장)
- GitHub 저장소: `https://github.com/SoohanMoon/Pdata`
- **중간점검 관련 파일이 GitHub에 푸시되어 있어야 합니다**
  - `midtermperformance.py`
  - `templates/performance/`
  - `중간점검/backdata_performance.csv`
  - `중간점검/project_nm.csv`

## 1단계: GitHub에 최신 코드 푸시

```bash
cd Pdata
git add .
git commit -m "변경사항 반영"
git push origin main
```

## 2단계: Railway 프로젝트 생성

1. [Railway 대시보드](https://railway.app/dashboard) → **New Project**
2. **Deploy from GitHub repo** 선택
3. `SoohanMoon/Pdata` 저장소 연결
4. 배포 브랜치: `main`

## 3단계: 환경변수 설정

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `SECRET_KEY` | (랜덤 긴 문자열) | Flask 세션 암호화 키 |
| `FLASK_DEBUG` | `False` | 프로덕션 디버그 비활성화 |
| `DATA_DIR` | `/data` | 영속 데이터 저장 경로 (볼륨 사용 시) |

## 4단계: 데이터 영속성 (볼륨) — 권장

1. Railway 서비스 → **Volumes** → **Add Volume**
2. 마운트 경로: `/data`
3. 환경변수 `DATA_DIR=/data` 설정

## 5단계: 도메인 확인

| 화면 | URL |
|------|-----|
| 메인 (목표등록) | `https://<도메인>/` |
| **중간점검 로그인 (국내)** | `https://<도메인>/midterm/` |
| 헬스체크 | `https://<도메인>/health` |

## 해외법인 별도 배포

| 항목 | 내용 |
|------|------|
| 저장소 | `https://github.com/SoohanMoon/dk-midterm-abroad` |
| Railway | 별도 프로젝트로 연결 |
| 로그인 URL | `https://<해외도메인>/midterm/` |

자세한 내용은 `dk-midterm-abroad` 저장소의 `RAILWAY_DEPLOYMENT.md`를 참고하세요.
