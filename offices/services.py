"""
services.py — 공공데이터 API 연동 + 실시간 스코어링 추천
"""

import math
import requests
from datetime import datetime
import concurrent.futures
from django.conf import settings
from django.core.cache import cache


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


def _fetch_all_pages(url: str, extra_params: dict = None) -> list:
    """페이징 자동 처리 — 전체 데이터 수집"""
    if extra_params is None: extra_params = {}
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
    민원실 기본정보 API (cso_info_v2) - 24시간 캐싱 적용
    """
    cached_offices = cache.get('office_info_list')
    if cached_offices is not None:
        return cached_offices
        
    try:
        items   = _fetch_all_pages(settings.OFFICE_INFO_API_URL)
        offices = []
        for item in items:
            offices.append({
                'id':         item.get('csoSn', ''),
                'name':       item.get('csoNm', ''),
                'address':    item.get('roadNmAddr') or item.get('lotnoAddr', ''),
                'lat':        float(item.get('lat', 0)),
                'lng':        float(item.get('lot', 0)),
                'open_time':  _parse_time(item.get('wkdyOperBgngTm', '090000')),
                'close_time': _parse_time(item.get('wkdyOperEndTm', '180000')),
                'night_open': item.get('nghtOperYn', 'N') == 'Y',
                'night_desc': item.get('nghtDowExpln', ''),
                'phone':      item.get('telno', ''),
            })
        cache.set('office_info_list', offices, 86400) # 24시간
        return offices
    except Exception as e:
        print(f"[fetch_office_list] Error: {e}")
        return _mock_offices()


def fetch_all_waiting() -> dict:
    """
    대기현황 전체를 한 번에 수집 - 60초 캐싱
    """
    cached_waiting = cache.get('office_waiting_dict')
    if cached_waiting is not None:
        return cached_waiting
        
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
        cache.set('office_waiting_dict', result, 60) # 1분
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
# 3. 카카오 API 함수
# ────────────────────────────────────────────────

def get_driving_time(lat1, lng1, lat2, lng2) -> float:
    """카카오모빌리티 길찾기 API 연동 - 예상 자동차 이동 시간 (분) 반환 (5분 캐싱)"""
    cache_key = f"kakao_navi_{round(lat1,4)}_{round(lng1,4)}_{round(lat2,4)}_{round(lng2,4)}"
    cached_time = cache.get(cache_key)
    if cached_time is not None:
        return cached_time
        
    api_key = getattr(settings, 'KAKAO_REST_API_KEY', '')
    if not api_key:
        # Fallback
        dist_km = haversine_km(lat1, lng1, lat2, lng2)
        fallback_val = dist_km / 0.5
        cache.set(cache_key, fallback_val, 300)
        return fallback_val

    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "origin": f"{lng1},{lat1}",
        "destination": f"{lng2},{lat2}",
        "priority": "RECOMMEND"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=3)
        if resp.status_code == 200:
            routes = resp.json().get('routes', [])
            if routes:
                duration_sec = routes[0].get('summary', {}).get('duration', 0)
                answer = duration_sec / 60.0
                cache.set(cache_key, answer, 300)
                return answer
    except Exception as e:
        print(f"[Kakao API Error] {e}")
        
    # API 실패 시
    dist_km = haversine_km(lat1, lng1, lat2, lng2)
    fallback_val = dist_km / 0.5
    cache.set(cache_key, fallback_val, 300)
    return fallback_val


def search_kakao_local_offices(user_lat, user_lng, query):
    cache_key = f"kakao_local_{round(user_lat,3)}_{round(user_lng,3)}_{query}"
    cached_docs = cache.get(cache_key)
    if cached_docs is not None:
        return cached_docs
        
    api_key = getattr(settings, 'KAKAO_REST_API_KEY', '')
    if not api_key:
        return []
        
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "query": query,
        "x": user_lng,
        "y": user_lat,
        "radius": 10000,
        "sort": "distance",
        "category_group_code": "PO3"
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=3)
        if resp.status_code == 200:
            docs = resp.json().get('documents', [])
            cache.set(cache_key, docs, 3600) # 1시간 캐시
            return docs
    except Exception as e:
        print("[Kakao Local Search Error]", e)
    return []


# ────────────────────────────────────────────────
# 4. 메인 추천 함수
# ────────────────────────────────────────────────

# 공공 API taskNm 필드와 매칭되는 키워드 목록
# 42개 민원실 공통으로 실시간 대기 창구가 있는 업무만 포함
API_TASK_MAPPING = {
    '여권':         ['여권'],
    '증명서 발급':  ['증명', '등초본', '등 초본', '인감증명', '가족관계', '민원발급'],
    '전입 신고':    ['전입'],
    '출생 신고':    ['출생'],
    '사망 신고':    ['사망'],
    '혼인 신고':    ['혼인'],
    '이혼 신고':    ['이혼'],
}


def recommend_offices_prediction(
    user_lat: float,
    user_lng: float,
    selected_service: str = '',
    top_n: int = 3,
    debug_mode: bool = False,
) -> list:
    """예측 모드 (42개 지자체 한정) - ThreadPool 병렬화 최적화"""
    import random
    offices     = fetch_office_list()
    
    if debug_mode:
        # 가상 테스트: 실제 API taskNm 키워드로 랜덤 대기인원 주입
        DEBUG_TASK_NAMES = ['여권', '증명', '민원발급', '인감증명', '가족관계', '등초본', '전입', '출생', '사망', '혼인', '이혼']
        waiting_all = {}
        for office in offices:
            waiting_all[office['id']] = {
                task: random.randint(0, 20)
                for task in DEBUG_TASK_NAMES
            }
        print("[DEBUG MODE] 랜덤 대기인원 주입 중")
    else:
        waiting_all = fetch_all_waiting()
    
    now = datetime.now()
    
    valid_offices = []
    
    for office in offices:
        cso_id      = office['id']
        waiting_map = waiting_all.get(cso_id, {})

        if selected_service and waiting_map:
            kws = API_TASK_MAPPING.get(selected_service, [selected_service])
            if not any(any(kw in nm for kw in kws) for nm in waiting_map.keys()):
                continue
            waiting_count = 0
            for nm, cnt in waiting_map.items():
                if any(kw in nm for kw in kws):
                    waiting_count += cnt
        else:
            waiting_count = sum(waiting_map.values()) if waiting_map else 0

        expected_wait_min = waiting_count * 3 
        distance_km = haversine_km(user_lat, user_lng, office['lat'], office['lng'])
        if distance_km > 30.0:
            continue
            
        try:
            h, m = map(int, office['close_time'].split(':'))
            close = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if office['night_open'] and now.hour >= 18:
                close = now.replace(hour=20, minute=0, second=0, microsecond=0)
            remain_min = (close - now).total_seconds() / 60
        except:
            remain_min = 1000
            
        if remain_min <= 0:
            continue

        valid_offices.append({
            'office': office,
            'expected_wait_min': expected_wait_min,
            'distance_km': distance_km,
            'waiting_count': waiting_count,
            'waiting_map': waiting_map
        })

    # ThreadPool을 활용한 병렬 네비게이션 시간 산출
    def _fetch_driving(vo):
        off = vo['office']
        dt = get_driving_time(user_lat, user_lng, off['lat'], off['lng'])
        vo['driving_time_min'] = dt
        return vo

    processed_offices = []
    # 요청마다 최대 10개의 스레드를 사용하여 동시에 통신
    if valid_offices:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            processed_offices = list(executor.map(_fetch_driving, valid_offices))
            
    results = []
    for vo in processed_offices:
        total_time_min = vo['driving_time_min'] + vo['expected_wait_min']
        office = vo['office']
        
        dist_km = vo['distance_km']
        walking_min = round((dist_km / 4.0 * 60) * 1.5)          # (거리÷4km/h) × 1.5
        transit_min = round((dist_km / 20.0 * 60 + 5) * 1.5)     # (거리÷20km/h + 환승5분) × 1.5

        results.append({
            'mode': 'PREDICTION',
            'id':             office['id'],
            'name':           office['name'],
            'address':        office['address'],
            'phone':          office['phone'],
            'lat':            office['lat'],
            'lng':            office['lng'],
            'distance_km':    round(dist_km, 1),
            'waiting_count':  vo['waiting_count'],
            'waiting_label':  _waiting_label(vo['waiting_count']),
            'available_tasks': list(vo['waiting_map'].keys()),
            'close_time':     office['close_time'],
            'night_open':     office['night_open'],
            'night_desc':     office['night_desc'],
            'times': {
                'driving':  round(vo['driving_time_min']),
                'walking':  walking_min,
                'transit':  transit_min,
                'waiting':  vo['expected_wait_min'],
                'total':    round(total_time_min),
            },
        })

    results.sort(key=lambda x: x['times']['total'])
    top = results[:top_n]
    badges = ['🏆 최적 추천(최단시간)', '✅ 2순위', '📍 3순위']
    for i, r in enumerate(top):
        r['rank']        = i + 1
        r['badge']       = badges[i] if i < len(badges) else ''
        r['tomorrow']    = False

    return top


def recommend_offices_general(
    user_lat: float,
    user_lng: float,
    selected_service: str = '',
    top_n: int = 3,
) -> list:
    """일반 모드 (전국 대상, 카카오 로컬 검색) - 병렬 최적화"""
    # 구청/시청 수준 업무 → '구청' 키워드로 검색
    CITY_HALL_SERVICES = ['여권 발급·재발급', '부동산 거래 신고', '자동차 취득세 신고', '장애인 등록', '기초생활 수급 신청', '혼인 신고', '이혼 신고']
    is_city_hall = selected_service in CITY_HALL_SERVICES

    try:
        if is_city_hall:
            docs = search_kakao_local_offices(user_lat, user_lng, '구청')
            if not docs:
                docs = search_kakao_local_offices(user_lat, user_lng, '시청')
        else:
            docs = search_kakao_local_offices(user_lat, user_lng, '행정복지센터')
    except Exception:
        docs = []

    target_docs = docs[:top_n]
    
    # ThreadPool을 사용한 병렬 소요시간 계산
    def _fetch_driving_for_doc(doc):
        dest_lat = float(doc.get('y', 0))
        dest_lng = float(doc.get('x', 0))
        dt = get_driving_time(user_lat, user_lng, dest_lat, dest_lng)
        doc['_driving_time'] = dt
        return doc
        
    if target_docs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=top_n) as executor:
            target_docs = list(executor.map(_fetch_driving_for_doc, target_docs))

    results = []
    for doc in target_docs:
        dest_lat = float(doc.get('y', 0))
        dest_lng = float(doc.get('x', 0))
        dist_m = int(doc.get('distance', 0))
        dist_km = dist_m / 1000.0
        driving_time_min = doc.get('_driving_time', dist_km / 0.5)

        walking_min = round((dist_km / 4.0 * 60) * 1.5)          # (거리÷4km/h) × 1.5
        transit_min = round((dist_km / 20.0 * 60 + 5) * 1.5)     # (거리÷20km/h + 환승5분) × 1.5

        results.append({
            'mode': 'GENERAL',
            'id':             doc.get('id'),
            'name':           doc.get('place_name'),
            'address':        doc.get('road_address_name') or doc.get('address_name'),
            'phone':          doc.get('phone', ''),
            'lat':            dest_lat,
            'lng':            dest_lng,
            'distance_km':    round(dist_km, 1),
            'waiting_count':  -1,
            'waiting_label':  '알 수 없음 ⚪',
            'available_tasks': [selected_service],
            'close_time':     '18:00',
            'night_open':     False,
            'night_desc':     '',
            'times': {
                'driving':  round(driving_time_min),
                'walking':  walking_min,
                'transit':  transit_min,
                'waiting':  0,
                'total':    round(driving_time_min),
            },
        })
        
    results.sort(key=lambda x: x['times']['total'])
    badges = ['🏆 가장 가까움', '✅ 2순위', '📍 3순위']
    for i, r in enumerate(results):
        r['rank']        = i + 1
        r['badge']       = badges[i] if i < len(badges) else ''
        r['tomorrow']    = False

    return results


def fetch_office_waiting(cso_sn: str) -> dict:
    # 단일 지점 캐싱 (api_waiting 뷰 등에서 호출될 경우)
    cache_key = f"waiting_{cso_sn}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        items = _fetch_all_pages(settings.WAITING_API_URL, {'csoSn': cso_sn})
        res = {item.get('taskNm', '기타'): int(item.get('wtngCnt', 0) or 0)
                for item in items}
        cache.set(cache_key, res, 60)
        return res
    except Exception as e:
        print(f"[fetch_office_waiting] {cso_sn} Error: {e}")
        return {}



# 42개 민원실 공공 API에서 공통 제공하는 업무만 포함
# (부동산 거래 신고, 차량 취득세는 실시간 대기 창구 없어 제외)
SERVICE_CHOICES = {
    '예측 모드 가능 업무 (42개 관공서 공통)': [
        '여권',
        '증명서 발급',
        '전입 신고',
        '출생 신고',
        '사망 신고',
        '혼인 신고',
        '이혼 신고',
    ]
}

# 일반 모드 서비스 목록 (카카오 로컬 검색 기반, 전국 대상)
GENERAL_SERVICE_CHOICES = {
    '📋 증명서 발급': [
        '주민등록 등·초본',
        '인감증명서',
        '가족관계증명서',
        '주민등록증 재발급',
    ],
    '📝 신고 업무': [
        '전입 신고',
        '출생 신고',
        '사망 신고',
        '혼인 신고',
        '이혼 신고',
    ],
    '🏛️ 시·구청 전문 업무': [
        '여권 발급·재발급',
        '부동산 거래 신고',
        '자동차 취득세 신고',
        '장애인 등록',
        '기초생활 수급 신청',
    ],
}


def _mock_offices():
    """API 타임아웃 시 사용하는 42개 관공서 하드코딩 데이터 (실제 좌표 기반)"""
    return [
        # 서울 (7개)
        {'id': 'CS_SEO_GN',  'name': '강남구청',     'address': '서울특별시 강남구 학동로 426',          'lat': 37.517352, 'lng': 127.047224, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-3423-5555'},
        {'id': 'CS_SEO_GD',  'name': '강동구청',     'address': '서울특별시 강동구 성내로 25',           'lat': 37.530134, 'lng': 127.123746, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-3425-5555'},
        {'id': 'CS_SEO_GJ',  'name': '광진구청',     'address': '서울특별시 광진구 아차산로 400',        'lat': 37.538526, 'lng': 127.082327, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-450-7114'},
        {'id': 'CS_SEO_GC',  'name': '금천구청',     'address': '서울특별시 금천구 시흥대로73길 70',     'lat': 37.456778, 'lng': 126.895403, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-2627-1000'},
        {'id': 'CS_SEO_MP',  'name': '마포구청',     'address': '서울특별시 마포구 월드컵로 212',        'lat': 37.566387, 'lng': 126.901942, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-3153-8000'},
        {'id': 'CS_SEO_SC',  'name': '서초구청',     'address': '서울특별시 서초구 남부순환로 2584',     'lat': 37.483597, 'lng': 127.032699, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-2155-6000'},
        {'id': 'CS_SEO_YD',  'name': '영등포구청',   'address': '서울특별시 영등포구 당산로 123',        'lat': 37.526273, 'lng': 126.895956, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '야간민원', 'phone': '02-2670-3114'},
        # 부산 (2개)
        {'id': 'CS_BS_BJ',   'name': '부산진구청',   'address': '부산광역시 부산진구 시민공원로 30',     'lat': 35.162769, 'lng': 129.053611, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '051-605-4000'},
        {'id': 'CS_BS_HU',   'name': '해운대구청',   'address': '부산광역시 해운대구 중동1로 20',        'lat': 35.160016, 'lng': 129.163753, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '051-749-4000'},
        # 대구 (2개)
        {'id': 'CS_DG_DS',   'name': '달서구청',     'address': '대구광역시 달서구 달구벌대로 1625',     'lat': 35.830434, 'lng': 128.532785, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '053-667-3000'},
        {'id': 'CS_DG_SS',   'name': '수성구청',     'address': '대구광역시 수성구 동대구로 376',        'lat': 35.858086, 'lng': 128.630692, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '053-666-2000'},
        # 인천 (3개)
        {'id': 'CS_IC_ND',   'name': '남동구청',     'address': '인천광역시 남동구 예술로 152',          'lat': 37.447222, 'lng': 126.731094, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '032-453-2000'},
        {'id': 'CS_IC_YS',   'name': '연수구청',     'address': '인천광역시 연수구 청량로102번길 40',    'lat': 37.410261, 'lng': 126.678621, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '032-749-7114'},
        {'id': 'CS_IC_BP',   'name': '부평구청',     'address': '인천광역시 부평구 부평대로 168',        'lat': 37.489271, 'lng': 126.723063, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '032-509-6114'},
        # 광주 (3개)
        {'id': 'CS_GJ_GS',   'name': '광산구청',     'address': '광주광역시 광산구 광산로29번길 10',     'lat': 35.139503, 'lng': 126.793461, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '062-960-8114'},
        {'id': 'CS_GJ_BK',   'name': '북구청',       'address': '광주광역시 북구 설죽로315번길 2',       'lat': 35.174798, 'lng': 126.912224, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '062-410-6114'},
        {'id': 'CS_GJ_SEO',  'name': '서구청(광주)', 'address': '광주광역시 서구 내방로 111',            'lat': 35.149667, 'lng': 126.858428, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '062-360-7114'},
        # 대전 (2개)
        {'id': 'CS_DJ_SEO',  'name': '서구청(대전)', 'address': '대전광역시 서구 둔산로 100',            'lat': 36.351609, 'lng': 127.385005, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '042-600-6114'},
        {'id': 'CS_DJ_YS',   'name': '유성구청',     'address': '대전광역시 유성구 대학로 82',           'lat': 36.362237, 'lng': 127.356328, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '042-611-2000'},
        # 울산 (2개)
        {'id': 'CS_US_NAM',  'name': '울산남구청',   'address': '울산광역시 남구 중앙로 201',            'lat': 35.538373, 'lng': 129.311475, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '052-226-5114'},
        {'id': 'CS_US_UJ',   'name': '울주군청',     'address': '울산광역시 울주군 울주군수로 6',         'lat': 35.519931, 'lng': 129.237854, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '052-229-7114'},
        # 경기도 (7개)
        {'id': 'CS_GG_GY',   'name': '고양시청',     'address': '경기도 고양시 덕양구 고양시청로 10',   'lat': 37.658074, 'lng': 126.832095, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-909-9000'},
        {'id': 'CS_GG_NJ',   'name': '남양주시청',   'address': '경기도 남양주시 다산지금로 57',         'lat': 37.636284, 'lng': 127.216101, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-590-2000'},
        {'id': 'CS_GG_SN',   'name': '성남시청',     'address': '경기도 성남시 중원구 성남대로 997',    'lat': 37.433553, 'lng': 127.139623, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-729-2114'},
        {'id': 'CS_GG_SW',   'name': '수원시청',     'address': '경기도 수원시 팔달구 효원로 241',      'lat': 37.263573, 'lng': 127.028601, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-228-2114'},
        {'id': 'CS_GG_AS',   'name': '안산시청',     'address': '경기도 안산시 단원구 화랑로 387',      'lat': 37.321426, 'lng': 126.830977, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-481-2114'},
        {'id': 'CS_GG_YI',   'name': '용인시청',     'address': '경기도 용인시 처인구 중부대로 1199',   'lat': 37.233749, 'lng': 127.205065, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-324-2114'},
        {'id': 'CS_GG_HS',   'name': '화성시청',     'address': '경기도 화성시 남양읍 시청로 159',      'lat': 37.199453, 'lng': 126.831736, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '031-369-2114'},
        # 강원도 (2개)
        {'id': 'CS_GW_WJ',   'name': '원주시청',     'address': '강원도 원주시 시청로 1',               'lat': 37.342089, 'lng': 127.920162, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '033-737-2114'},
        {'id': 'CS_GW_CC',   'name': '춘천시청',     'address': '강원도 춘천시 시청길 11',              'lat': 37.881600, 'lng': 127.729803, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '033-250-3114'},
        # 충청북도 (1개)
        {'id': 'CS_CB_CJ',   'name': '청주시청',     'address': '충청북도 청주시 상당구 상당로 155',    'lat': 36.641541, 'lng': 127.486140, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '043-201-1114'},
        # 충청남도 (2개)
        {'id': 'CS_CN_AS',   'name': '아산시청',     'address': '충청남도 아산시 시청로 22',            'lat': 36.789802, 'lng': 127.003745, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '041-537-2114'},
        {'id': 'CS_CN_CA',   'name': '천안시청',     'address': '충청남도 천안시 서북구 시청로 1',      'lat': 36.814988, 'lng': 127.113611, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '041-521-2114'},
        # 전라북도 (1개)
        {'id': 'CS_JB_JJ',   'name': '전주시청',     'address': '전라북도 전주시 완산구 노송광장로 10', 'lat': 35.824215, 'lng': 127.148013, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '063-281-2114'},
        # 전라남도 (2개)
        {'id': 'CS_JN_SC',   'name': '순천시청',     'address': '전라남도 순천시 장명로 30',            'lat': 34.950855, 'lng': 127.487262, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '061-749-3114'},
        {'id': 'CS_JN_YS',   'name': '여수시청',     'address': '전라남도 여수시 시청로 1',             'lat': 34.761720, 'lng': 127.661944, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '061-659-2114'},
        # 경상북도 (3개)
        {'id': 'CS_GB_GJ',   'name': '경주시청',     'address': '경상북도 경주시 동금동길 1',           'lat': 35.856398, 'lng': 129.224825, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '054-779-6114'},
        {'id': 'CS_GB_GM',   'name': '구미시청',     'address': '경상북도 구미시 송정대로 20',          'lat': 36.119485, 'lng': 128.344085, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '054-480-2114'},
        {'id': 'CS_GB_PH',   'name': '포항시청',     'address': '경상북도 포항시 남구 시청로 1',        'lat': 36.019558, 'lng': 129.343671, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '054-270-2114'},
        # 경상남도 (2개)
        {'id': 'CS_GN_KH',   'name': '김해시청',     'address': '경상남도 김해시 가락로 167',           'lat': 35.228518, 'lng': 128.889459, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '055-330-2114'},
        {'id': 'CS_GN_CW',   'name': '창원시청',     'address': '경상남도 창원시 의창구 중앙대로 300', 'lat': 35.227133, 'lng': 128.681530, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '055-225-2114'},
        # 제주 (1개)
        {'id': 'CS_JJ_JJ',   'name': '제주시청',     'address': '제주특별자치도 제주시 문연로 6',       'lat': 33.499620, 'lng': 126.531356, 'open_time': '09:00', 'close_time': '18:00', 'night_open': False, 'night_desc': '', 'phone': '064-728-2114'},
    ]

