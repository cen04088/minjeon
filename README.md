# 🏛️ 민원ON — 실시간 민원실 대기현황 통합 서비스

> 전국 지자체 민원실 실시간 대기현황을 한 곳에서 조회하고,  
> 위치 기반 스코어링 알고리즘으로 가장 빠른 민원실을 추천하는 모바일 웹서비스

---

## 🚀 빠른 시작

### 로컬 실행
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 3. DB 마이그레이션 (PostgreSQL 또는 SQLite)
python manage.py migrate

# 4. 서버 실행
python manage.py runserver
```

### Railway 배포
```bash
git init
git add .
git commit -m "init: 민원ON 프로젝트"
git remote add origin https://github.com/YOUR_ID/minjeon.git
git push -u origin main
```
이후 Railway에서 GitHub 연결 → PostgreSQL 추가 → 환경변수 설정

---

## ⚙️ 환경변수 (.env)

| 변수명 | 설명 |
|---|---|
| `SECRET_KEY` | Django 시크릿 키 (랜덤 문자열) |
| `DEBUG` | 개발: `True` / 배포: `False` |
| `PUBLIC_DATA_API_KEY` | data.go.kr 발급 API 키 |
| `WAITING_API_URL` | 민원실 실시간 대기현황 API 엔드포인트 |
| `OFFICE_INFO_API_URL` | 민원실 기본정보 API 엔드포인트 |
| `PGDATABASE` / `PGUSER` / ... | PostgreSQL 접속 정보 (Railway 자동 주입) |

---

## 🔌 API 연동 가이드

`offices/services.py` 의 두 함수를 실제 API 응답 구조에 맞게 수정합니다.

### fetch_office_list() — 민원실 기본정보
```python
# data.go.kr API 응답 예시에 맞게 키 이름 수정
'id':         item.get('민원실ID'),     # ← 실제 응답 키로 교체
'name':       item.get('민원실명'),
'lat':        float(item.get('위도')),
'lng':        float(item.get('경도')),
'close_time': item.get('운영종료시간'),
'services':   item.get('취급업무', '').split(','),
```

### fetch_waiting_status() — 실시간 대기현황
```python
service_type  = item.get('업무유형')   # ← 실제 응답 키로 교체
waiting_count = int(item.get('대기인원'))
```

> API 키가 없거나 오류 발생 시 서울 6개 구청 목 데이터로 자동 대체됩니다.

---

## 📡 서비스 엔드포인트

| URL | 설명 |
|---|---|
| `GET /` | 메인 페이지 (위치 탐지 + 업무 선택) |
| `GET /recommend/` | 추천 결과 페이지 |
| `GET /api/recommend/` | 추천 결과 JSON API |
| `GET /api/waiting/` | 특정 민원실 대기현황 JSON |

---

## 🧮 추천 스코어링 로직

```
종합점수 (100점) =
  대기인원 점수 (40점)   — 대기 0명=40점, 25명 초과=0점
+ 거리 점수     (30점)   — 500m이내=30점, 10km초과=0점
+ 운영시간 점수 (20점)   — 2시간이상여유=20점, 종료=제외
+ 업무가용 점수 (10점)   — 해당업무취급=10점, 미취급=제외
```

**추천 모드 3종:**
- ⚖️ **SMART** — 균형 (기본)
- ⚡ **FAST** — 대기인원 가중치 1.5배
- 📍 **NEAR** — 거리 가중치 1.5배

---

## 🗂️ 프로젝트 구조

```
minjeon/
├── config/
│   ├── settings.py      # Django 설정
│   └── urls.py
├── offices/
│   ├── services.py      # API 연동 + 추천 알고리즘 (핵심)
│   ├── views.py         # 뷰 + REST API
│   └── urls.py
├── templates/
│   ├── base.html
│   └── offices/
│       ├── index.html   # 메인 (GPS + 업무선택)
│       └── result.html  # TOP3 추천 결과
├── static/
│   ├── css/style.css
│   └── js/main.js       # GPS 위치 탐지
├── Procfile             # Railway 실행 명령
├── railway.toml
└── requirements.txt
```
