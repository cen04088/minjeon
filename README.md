# 🏛️ 민원ON (Minwon ON)
### "당신의 시간은 소중하니까, 대기 시간까지 계산하는 똑똑한 민원 안내"

**2026 전국 통합데이터 활용 공모전 출품작**  
전국 지자체 민원실의 실시간 대기현황과 위치 기반 이동 시간을 결합하여, 시민들에게 **'가장 빠르게 민원을 처리할 수 있는 장소'**를 추천하는 지능형 모바일 웹 플랫폼입니다.

---

## 🌟 핵심 가치 (Core Values)
현대인의 **'시간 빈곤(Time Poor)'** 문제를 공공데이터로 해결합니다. 단순히 가까운 곳이 아닌, **[이동 시간 + 대기 시간]**이 최소화되는 최적의 장소를 AI 알고리즘이 실시간으로 도출합니다.

## ✨ 주요 기능 (Key Features)

### 1. 지능형 듀얼 탐색 모드
*   **⏱️ 실시간 예측 모드 (Premium):** 42개 주요 지자체(서울, 경기 등)의 실시간 번호표 데이터를 연동하여 1분 단위의 대기 현황을 반영합니다.
*   **🌐 전국 일반 모드 (Standard):** 카카오 로컬 검색 API를 통해 전국 모든 행정복지센터와 시·구청을 탐색합니다. (예측 데이터 부재 시 자동 폴백 지원)

### 2. 🚗 카카오 모빌리티 엔진 통합
*   단순 직선 거리가 아닌, 실제 도로 상황을 반영한 **자동차 주행 시간**을 산출합니다.
*   도보 및 대중교통 예상 소요 시간을 분석하여 다각도의 이동 편의성을 제공합니다.

### 3. 🤖 AI 민원 준비물 도우미 (Powered by Gemini)
*   "여권 발급할 때 뭐 필요해?"와 같은 자연어 질문에 즉각 대응합니다.
*   기관 방문 전 필수 서류를 미리 안내하여 **'서류 누락으로 인한 재방문(헛걸음)'**을 원천 차단합니다.

### 4. 📱 모바일 퍼스트 & PWA
*   별도의 앱 설치 없이 웹에서 즉시 실행 가능한 **PWA(Progressive Web App)** 기술을 적용했습니다.
*   홈 화면 추가 기능을 통해 앱처럼 편리하게 접근할 수 있습니다.

---

## 🛠️ 기술 스택 (Tech Stack)
*   **Backend:** Python 3.10+, Django 4.2
*   **Frontend:** Vanilla JavaScript (ES6+), Modern CSS3 (Glassmorphism UI)
*   **AI/LLM:** Google Gemini 1.5/2.5 Flash
*   **Storage:** SQLite (Development) / PostgreSQL (Production)
*   **APIs:** 
    *   공공데이터포털 (실시간 대기현황, 민원실 정보)
    *   Kakao Mobility (Directions API)
    *   Kakao Local (Keyword Search API)

---

## ⚙️ 환경 설정 (.env)
본 프로젝트를 구동하기 위해 다음 API 키들이 필요합니다.

```ini
# Django
SECRET_KEY=your_secret_key
DEBUG=True

# 공공데이터 API (data.go.kr)
PUBLIC_DATA_API_KEY=your_key
WAITING_API_URL=실시간_대기현황_엔드포인트
OFFICE_INFO_API_URL=민원실_기본정보_엔드포인트

# Kakao Developers
KAKAO_REST_API_KEY=your_rest_api_key
KAKAO_JS_API_KEY=your_javascript_key

# Generative AI
GEMINI_API_KEY=your_gemini_key
```

---

## 📈 추천 알고리즘 (Total-Time Minimization)
민원ON은 단순한 거리순 정렬을 지양하고, 다음의 수식으로 최적의 장소를 결정합니다.

$$ \text{Total Time} = \text{Driving Duration (Kakao)} + (\text{Waiting Count} \times 3 \text{ min}) $$

*   **1순위 (🏆 최단시간):** 총 소요 시간이 가장 적은 기관
*   **2순위 (✅ 차선책):** 안정적인 업무 처리가 가능한 대기 인원 적은 기관

---

## 🏗️ 설치 및 실행 안내 (Setup)

1. **저장소 클론 및 패키지 설치**
   ```bash
   pip install -r requirements.txt
   ```
2. **데이터베이스 마이그레이션**
   ```bash
   python manage.py migrate
   ```
3. **로컬 서버 기동**
   ```bash
   python manage.py runserver
   ```

---

## ✉️ 문의 및 피드백
본 서비스는 열린 데이터를 통해 국민의 삶의 질을 높이기 위해 끊임없이 진화하고 있습니다. 기획안 및 기술 문의는 개발팀으로 연락 주시기 바랍니다.
