# Railway 배포 가이드 — 동국홀딩스 2026 평가시스템

목표등록 + **중간점검** 시스템을 Railway에 배포하는 방법입니다.

## 사전 준비

- [Railway](https://railway.app) 계정 (GitHub 로그인 권장)
- GitHub 저장소: `https://github.com/SoohanMoon/Pdata`
- **중간점검 관련 파일이 GitHub에 푸시되어 있어야 합니다**
  - `midtermperformance.py`
  - `templates/performance/`
  - `중간점검/backdata_performance.csv`
  - `중간점검/project_nm.csv`

## 1단계: GitHub에 최신 코드 푸시

로컬 변경사항을 커밋·푸시합니다.

```bash
cd Pdata
git add .
git commit -m "중간점검 시스템 및 Railway 배포 설정 추가"
git push origin main
```

## 2단계: Railway 프로젝트 생성

1. [Railway 대시보드](https://railway.app/dashboard) → **New Project**
2. **Deploy from GitHub repo** 선택
3. `SoohanMoon/Pdata` 저장소 연결
4. 배포 브랜치: `main`

## 3단계: 환경변수 설정

Railway 서비스 → **Variables** 탭에서 아래를 추가합니다.

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `SECRET_KEY` | (랜덤 긴 문자열) | Flask 세션 암호화 키 |
| `FLASK_DEBUG` | `False` | 프로덕션 디버그 비활성화 |
| `DATA_DIR` | `/data` | 영속 데이터 저장 경로 (볼륨 사용 시) |

`SECRET_KEY` 예시 생성 (PowerShell):

```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

## 4단계: 데이터 영속성 (볼륨) — 권장

Railway는 기본적으로 **재배포 시 파일이 초기화**됩니다.  
목표(`goals.json`)와 중간실적(`performance_data.json`)을 유지하려면 **Volume**을 추가하세요.

1. Railway 서비스 → **Volumes** → **Add Volume**
2. 마운트 경로: `/data`
3. 환경변수 `DATA_DIR=/data` 설정 (3단계)

## 5단계: 도메인 확인

1. 서비스 → **Settings** → **Networking** → **Generate Domain**
2. 배포 완료 후 아래 URL로 접속합니다.

| 화면 | URL |
|------|-----|
| 메인 (목표등록) | `https://<도메인>/` |
| **중간점검 로그인** | `https://<도메인>/midterm/` |
| 헬스체크 | `https://<도메인>/health` |

## 배포 후 점검 체크리스트

- [ ] `/health` → `{"status":"ok"}` 응답
- [ ] `/` 메인 페이지 로드
- [ ] `/midterm/` 중간점검 로그인 화면 로드
- [ ] 팀원 계정으로 실적등록 테스트
- [ ] 팀장 계정으로 실적조회 테스트
- [ ] 관리자(ID: `11210110`) 로그인 테스트
- [ ] 재배포 후에도 등록 데이터 유지 (볼륨 설정 시)

## 문제 해결

### 배포 실패

- Railway **Deployments** → **View Logs**에서 빌드/시작 오류 확인
- `requirements.txt` 패키지 설치 오류 여부 확인

### 502 / 앱이 안 뜸

- `gunicorn_config.py`의 `PORT` 바인딩 확인 (Railway가 자동 주입)
- `/health` 헬스체크 경로 응답 확인

### 로그인은 되는데 데이터가 사라짐

- Volume 미설정 시 정상 동작 (재배포마다 초기화)
- `DATA_DIR=/data` + Volume 마운트 필요

### 중간점검 로그인 오류

- `중간점검/backdata_performance.csv`가 GitHub에 포함됐는지 확인
- Railway 로그에서 CSV 로드 오류 메시지 확인

## 로컬 vs Railway

| 항목 | 로컬 | Railway |
|------|------|---------|
| 실행 | `python app.py` | gunicorn (Procfile) |
| 포트 | 5001 (기본) | Railway `PORT` 자동 |
| 데이터 | `Pdata/` 폴더 | `DATA_DIR` (볼륨 권장) |
