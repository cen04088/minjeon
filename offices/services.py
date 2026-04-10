"""
services.py — 공공데이터 API 연동 + 실시간 스코어링 추천
"""

import math
import requests
from datetime import datetime
from django.conf import settings


# ────────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────────

def _parse_time(raw: str) -> str:
    """'090000' → '09:00'"""
    raw = str(raw).zfill(6)
    return f"{raw[:2]}:{raw[2:4]}"


def _waiting_label(count: int) -> str:
    if count == 0:   return '없음 🟢'
    if count <= 5:   return '여유 🟢'
    if count <= 15:  return '보통 🟡'
    if count <= 25:  return '혼잡 🟠'
    return '매우 혼잡 🔴'


def _fetch_all_pages(url: str, extra_params: dict = {}) -> list:
    """페이징 자동 처리 — 전체 데이터 수집"""
    all_items, page = [], 1
    while True:
        resp = requests.get(
            url,
            params={'serviceKey': settings.PUBLIC_DATA_API_KEY,
                    'pageNo': page, 'numOfRows': 100, 'type': 'json',
                    **extra_params},
            timeout=10,
        )
        resp.raise_for_status()
        body  = resp.json().get('body', {})
        items = body.get('items', {}).get('item', [])
        if isinstance(items, dict):
            items = [items]
        total = int(body.get('totalCount', 0))
        all_items.extend(items)
        if len(all_items) >= total or not items:
            break
        page += 1
    return all_items


# ────────────────────────────────────────────────
# 1. 공공데이터 API 호출
# ────────────────────────────────────────────────

def fetch_office_list() -> list:
    """
    민원실 기본정보 API (cso_info_v2)
    확정 키: csoSn, csoNm, roadNmAddr, lat, lot,
             wkdyOperBgngTm, wkdyOperEndTm, nghtOperYn, nghtDowExpln
    """
    try:
        items   = _fetch_all_pages(settings.OFFICE_INFO_API_URL)
        offices = []
        for item in items:
            offices.append({
                'id':         item.get('csoSn', ''),
                'name':       item.get('csoNm', ''),
                'address':    item.get('roadNmAddr') or item.get('lotnoAddr', ''),
                'lat':        float(item.get('lat', 0)),
                'lng':        float(item.get('lot', 0)),   # 경도 키가 'lot'
                'open_time':  _parse_time(item.get('wkdyOperBgngTm', '090000')),
                'close_time': _parse_time(item.get('wkdyOperEndTm', '180000')),
                'night_open': item.get('nghtOperYn', 'N') == 'Y',
                'night_desc': item.get('nghtDowExpln', ''),
                'phone':      item.get('telno', ''),
            })
        return offices
    except Exception as e:
        print(f"[fetch_office_list] Error: {e}")
        return _mock_offices()


def fetch_all_waiting() -> dict:
    """
    대기현황 전체를 한 번에 수집 → {csoSn: {taskNm: wtngCnt, ...}, ...}
    확정 키: csoSn, taskNm, wtngCnt

    민원실마다 개별 호출하면 41번 → 1번으로 해결
    """
    try:
        items  = _fetch_all_pages(settings.WAITING_API_URL)
        result = {}
        for item in items:
            cso_sn   = item.get('csoSn', '')
            task_nm  = item.get('taskNm', '기타')
            wtng_cnt = int(item.get('wtngCnt', 0) or 0)
            if cso_sn not in result:
                result[cso_sn] = {}
            result[cso_sn][task_nm] = wtng_cnt
        return result
    except Exception as e:
        print(f"[fetch_all_waiting] Error: {e}")
        return {}


# ────────────────────────────────────────────────
# 2. 거리 계산 (Haversine)
# ────────────────────────────────────────────────

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ────────────────────────────────────────────────
# 3. 스코어링 함수
# ────────────────────────────────────────────────

def score_waiting(count: int) -> int:
    """대기인원 점수 (40점)"""
    if count == 0:   return 40
    if count <= 3:   return 35
    if count <= 7:   return 25
    if count <= 15:  return 15
    if count <= 25:  return 5
    return 0


def score_distance(km: float) -> int:
    """거리 점수 (30점)"""
    if km <= 0.5:    return 30
    if km <= 1.0:    return 25
    if km <= 2.0:    return 20
    if km <= 5.0:    return 12
    if km <= 10.0:   return 5
    return 0


def score_time(close_time: str, night_open: bool, tomorrow_mode: bool = False) -> int:
    """
    운영시간 여유 점수 (20점)
    tomorrow_mode=True 이면 내일 기준 — 운영 종료 무시하고 전부 20점
    """
    if tomorrow_mode:
        return 20
    try:
        now = datetime.now()
        h, m = map(int, close_time.split(':'))
        close = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if night_open and now.hour >= 18:
            close = now.replace(hour=20, minute=0, second=0, microsecond=0)
        remain = (close - now).total_seconds() / 60
        if remain <= 0:    return -9999
        if remain >= 120:  return 20
        if remain >= 60:   return 12
        if remain >= 30:   return 5
        return 0
    except Exception:
        return 10


def score_service(selected: str, waiting_map: dict) -> int:
    """
    업무 가용 점수 (10점)
    대기현황 API의 taskNm 목록에서 선택 업무 포함 여부 확인
    """
    if not selected:
        return 10   # 전체 선택 → 모든 민원실 대상
    if not waiting_map:
        return 5    # 대기 데이터 없으면 중립
    for task_nm in waiting_map:
        if selected in task_nm:
            return 10
    return -9999    # 해당 업무 없음 → 추천 제외


def get_mode_weights(mode: str) -> dict:
    weights = {
        'SMART': {'waiting': 1.0, 'distance': 1.0, 'time': 1.0},
        'FAST':  {'waiting': 1.5, 'distance': 0.5, 'time': 1.0},
        'NEAR':  {'waiting': 0.5, 'distance': 1.5, 'time': 1.0},
    }
    return weights.get(mode, weights['SMART'])


# ────────────────────────────────────────────────
# 4. 메인 추천 함수
# ────────────────────────────────────────────────

def recommend_offices(
    user_lat: float,
    user_lng: float,
    selected_service: str = '',
    mode: str = 'SMART',
    top_n: int = 3,
) -> list:
    """
    실시간 스코어링 기반 민원실 TOP N 추천
    API 호출: 기본정보 1회 + 대기현황 1회 (총 2회)
    """
    offices     = fetch_office_list()
    waiting_all = fetch_all_waiting()   # 전체 대기현황 한 번에
    weights     = get_mode_weights(mode)
    results     = []

    for office in offices:
        cso_id      = office['id']
        waiting_map = waiting_all.get(cso_id, {})

        # 선택 업무의 대기인원 / 전체 선택이면 합산
        if selected_service and waiting_map:
            waiting_count = next(
                (cnt for nm, cnt in waiting_map.items() if selected_service in nm), 0
            )
        else:
            waiting_count = sum(waiting_map.values()) if waiting_map else 0

        # 취급 업무 목록 (대기현황 API의 taskNm 목록)
        available_tasks = list(waiting_map.keys())

        distance_km = haversine_km(user_lat, user_lng, office['lat'], office['lng'])

        s_wait    = score_waiting(waiting_count)                         * weights['waiting']
        s_dist    = score_distance(distance_km)                          * weights['distance']
        s_time    = score_time(office['close_time'], office['night_open']) * weights['time']
        s_service = score_service(selected_service, waiting_map)

        total = s_wait + s_dist + s_time + s_service

        if s_time <= -9000 or s_service <= -9000:
            continue

        results.append({
            'id':             cso_id,
            'name':           office['name'],
            'address':        office['address'],
            'phone':          office['phone'],
            'lat':            office['lat'],
            'lng':            office['lng'],
            'distance_km':    round(distance_km, 1),
            'waiting_count':  waiting_count,
            'waiting_label':  _waiting_label(waiting_count),
            'available_tasks': available_tasks,
            'close_time':     office['close_time'],
            'night_open':     office['night_open'],
            'night_desc':     office['night_desc'],
            'scores': {
                'waiting':  round(s_wait),
                'distance': round(s_dist),
                'time':     round(s_time),
                'service':  round(s_service),
                'total':    round(total),
            },
        })

    results.sort(key=lambda x: x['scores']['total'], reverse=True)
    top = results[:top_n]

    # ── 현재 운영 중인 민원실이 없으면 내일 기준으로 재시도 ──
    tomorrow_mode = False
    if not top:
        tomorrow_mode = True
        results = []
        for office in offices:
            cso_id      = office['id']
            waiting_map = waiting_all.get(cso_id, {})
            waiting_count = (
                next((cnt for nm, cnt in waiting_map.items() if selected_service in nm), 0)
                if selected_service and waiting_map
                else sum(waiting_map.values()) if waiting_map else 0
            )
            distance_km = haversine_km(user_lat, user_lng, office['lat'], office['lng'])
            s_wait    = score_waiting(waiting_count)                              * weights['waiting']
            s_dist    = score_distance(distance_km)                               * weights['distance']
            s_time    = score_time(office['close_time'], office['night_open'], tomorrow_mode=True) * weights['time']
            s_service = score_service(selected_service, waiting_map)
            total = s_wait + s_dist + s_time + s_service
            if s_service <= -9000:
                continue
            results.append({
                'id':             cso_id,
                'name':           office['name'],
                'address':        office['address'],
                'phone':          office['phone'],
                'lat':            office['lat'],
                'lng':            office['lng'],
                'distance_km':    round(distance_km, 1),
                'waiting_count':  waiting_count,
                'waiting_label':  _waiting_label(waiting_count),
                'available_tasks': list(waiting_map.keys()),
                'close_time':     office['close_time'],
                'night_open':     office['night_open'],
                'night_desc':     office['night_desc'],
                'scores': {
                    'waiting':  round(s_wait),
                    'distance': round(s_dist),
                    'time':     round(s_time),
                    'service':  round(s_service),
                    'total':    round(total),
                },
            })
        results.sort(key=lambda x: x['scores']['total'], reverse=True)
        top = results[:top_n]

    badges = ['🏆 최적 추천', '✅ 차선', '📍 대안']
    for i, r in enumerate(top):
        r['rank']        = i + 1
        r['badge']       = badges[i] if i < len(badges) else ''
        r['tomorrow']    = tomorrow_mode  # 템플릿에서 "내일 기준" 안내에 활용

    return top


# ────────────────────────────────────────────────
# 5. 단건 조회용 (result 페이지 새로고침)
# ────────────────────────────────────────────────

def fetch_office_waiting(cso_sn: str) -> dict:
    """특정 민원실 대기현황만 조회 → {taskNm: wtngCnt}"""
    try:
        items = _fetch_all_pages(settings.WAITING_API_URL, {'csoSn': cso_sn})
        return {item.get('taskNm', '기타'): int(item.get('wtngCnt', 0) or 0)
                for item in items}
    except Exception as e:
        print(f"[fetch_office_waiting] {cso_sn} Error: {e}")
        return {}


# ────────────────────────────────────────────────
# 6. 서비스 선택지 추출 (index 페이지 동적 생성용)
# ────────────────────────────────────────────────

# 실제 API의 taskNm 기반 서비스 목록 (cso_realtime_v2 응답에서 확인)
SERVICE_CHOICES = [
    '출생,혼인/이혼,사망',
    '체류지변경/면허증',
    '등본,인감/가족관계',
    '부동산거래 신고',
    '차량 취득세',
    '여권',
]


# ────────────────────────────────────────────────
# 7. 목 데이터 (API 오류 시 대체)
# ────────────────────────────────────────────────

def _mock_offices():
    return [
        {'id': 'CS0001', 'name': '광진구청',   'address': '서울특별시 광진구 아차산로 400',    'lat': 37.536399, 'lng': 127.088006, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 목요일 20시까지', 'phone': ''},
        {'id': 'CS0002', 'name': '마포구청',   'address': '서울 마포구 월드컵로 212',          'lat': 37.566387, 'lng': 126.901942, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 월요일 20시까지', 'phone': ''},
        {'id': 'CS0005', 'name': '서초구청',   'address': '서울 서초구 남부순환로 2584',        'lat': 37.483597, 'lng': 127.032699, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 수요일 20시까지', 'phone': ''},
        {'id': 'CS0004', 'name': '영등포구청', 'address': '서울 영등포구 당산로 123',           'lat': 37.526273, 'lng': 126.895956, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 화요일 20시까지', 'phone': ''},
        {'id': 'CS0006', 'name': '강동구청',   'address': '서울 강동구 성내로 25',             'lat': 37.530134, 'lng': 127.123746, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 화요일 20시까지', 'phone': ''},
        {'id': 'CS0003', 'name': '금천구청',   'address': '서울 금천구 시흥대로73길 70',        'lat': 37.456778, 'lng': 126.895403, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 목요일 20시까지', 'phone': ''},
    ]
